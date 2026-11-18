# ruff: noqa: E501
"""P10IR rehearsal (ADR-0029 sections 11 gate 5 and 13): every registered stage's code path end to end against a plan of its own, on a synthetic memory and on one rehearsal-trained tree cell and one flat cell,
and gates 1 and 2 on the registered checkpoints themselves.

* ``synthetic``: tiny sizes, the unit-test seeds (938001-938999), a random backbone. The miniature P10-S1 run (checkpoints and evaluation records) is made by P10-S1's OWN ``train.run_job`` and
  ``evaluate.evaluate_cell`` (seed-set names ``p10s1-test-<k>`` carry the test-range values; this is a test device, never a registered seed), so that stage A1's reads and gates 2 and 3, and the adapter identity
  gate, compare against what P10-S1's code produced. Stage A2 trains its own cells through the adapter.
* ``real``: one T-OQ and one F-OQ cell at 32,768 facts and 16,384 slots, the rehearsal draw 299201 with initialisation 330692, trained 64 updates through the adapter and read by the same stages through the
  process pool: seconds per read and peak memory of the all-keys reads are recorded (section 14).
* ``gates12``: gate 1 and gate 2 on every registered A1 checkpoint (the counts are already seen: this observes nothing new and catches platform or library drift before Decision 2; gate 3 is NOT run: the seal)
  and the adapter identity gate on P10-S1's registered draw-1 cells.

The rehearsal writes only under its own run directory. It opens no sealed value and writes nothing under P10-S1's run directory or the experiments of any registered study.
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from arborlm.io import file_sha256, write_json
from studies.p10s1 import core as s1core
from studies.p10s1 import evaluate as s1eval
from studies.p10s1 import train as s1train

from . import adapter, core, freeze, gates, items, labels, runner, stages
from . import plan as planmod
from .plan import Plan
from .stages_io import safe_name


def snapshots_of(spec: core.CellSpec) -> tuple[int, ...]:
    """The synthetic cell's snapshots: its four checkpoints (two trajectory points, U_P and the run length)."""
    return tuple(sorted(set(spec.checkpoints())))


def synthetic_specs(cfg: Any) -> list[core.CellSpec]:
    r = cfg["rehearsal"]
    u_p, run = int(r["synthetic_snapshots"][0]), int(r["synthetic_snapshots"][1])
    quarter = max(1, u_p // 2)
    return [core.CellSpec(int(r["synthetic_facts"]), int(n), "primary", u_p, run, (quarter, run - quarter)) for n in r["synthetic_slots"]]


def _mini_seed_a1(k: int) -> dict[str, Any]:
    return {"name": f"p10s1-test-{k}", "base": 938001 + 100 * k}  # the P10-S1 whitelist accepts the name; the values are the test range's


def _mini_seed_a2(k: int) -> dict[str, Any]:
    return {"name": f"p10ir-test-{k}", "base": 938001 + 100 * k}


def _write_manifest(root: Path, name: str, data: Any) -> Path:
    path = root / "draws" / name / "data_manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, {"sha256s": data.sha256s()})
    return path


def make_synthetic_s1_run(root: Path, specs: list[core.CellSpec], draws: int, ctx: items.Ctx, init_seed: int) -> dict[str, Any]:
    """The miniature P10-S1 run, by P10-S1's own training (``train.run_job`` in calibration mode) and evaluation (``evaluate.evaluate_cell``)."""
    out: dict[str, Any] = {"cells": [], "manifests": {}}
    bb = items.backbone_of(ctx)
    for d in range(1, draws + 1):
        seed = _mini_seed_a1(d - 1)
        probe = {"seed_name": seed["name"], "seed_base": seed["base"], "table_facts": ctx.sizes["table_facts"], "unseen": ctx.sizes["unseen"]}
        data, seeds = items.load_data(ctx, probe, verify=False)
        out["manifests"][seed["name"]] = str(_write_manifest(root, seed["name"], data))
        for spec in specs:
            for arm in ("T-OQ", "F-OQ"):
                cell = s1core.make_cell("P", arm, spec.facts, spec.slots, d, init_seed, u_p=spec.u_p, run_updates=spec.run)
                folder = root / "cells" / cell.label
                job = s1train.TrainJob(
                    cell=cell, data=data, stream=s1train.training_stream_for(data, cell.facts), backbone=bb, out_dir=folder, r1_seed=seeds.r1_codes, hash_seed=s1core.h8_seed(seeds), mode="calibration",
                    updates=cell.run_updates, snapshots=snapshots_of(spec), optimizer_marks=(cell.run_updates,), log_every=4,
                )  # fmt: skip
                s1train.train_cell(job)
                s1eval.evaluate_cell(cell, root, data, bb, readouts=list(snapshots_of(spec)), deep_at=cell.u_p, r1_seed=seeds.r1_codes, hash_seed=s1core.h8_seed(seeds), rows=None, require_train_record=True)
                out["cells"].append(cell.label)
    return out


def digests_of(root: Path, itemlist: list[dict[str, Any]]) -> dict[str, str]:
    return {f"{it['cell']}|{it['update']}": file_sha256(root / "cells" / it["cell"] / "snapshots" / s1core.snapshot_stem(it["update"]) / "model.pt") for it in itemlist}


def build_synthetic_plan(root: Path, cfg: Any, draws: int) -> tuple[Plan, items.Ctx]:
    """The synthetic phase's own plan (mode ``rehearsal``, ``freeze/plan.json`` of this phase) with the miniature P10-S1 run made and every item listed."""
    specs = synthetic_specs(cfg)
    sizes = {"table_facts": 512, "unseen": 64}
    root.mkdir(parents=True, exist_ok=True)
    ctx = items.Ctx("rehearsal", root, root / "s1", None, synthetic=True, run_sealed=True, sizes=sizes, index_seeds=core.i64_seeds(cfg, test=True))
    init_a1, init_a2 = int(cfg["seeds"]["test_init"][0]), int(cfg["seeds"]["test_init"][1])
    s1_root = root / "s1"
    made = make_synthetic_s1_run(s1_root, specs, draws, ctx, init_a1)

    def label_a1(arm: str, s: core.CellSpec, d: int) -> str:
        return s1core.make_cell("P", arm, s.facts, s.slots, d, init_a1, u_p=s.u_p, run_updates=s.run).label

    def label_a2(arm: str, s: core.CellSpec, d: int) -> str:
        return s1core.make_cell("P", arm, s.facts, s.slots, d, init_a2, u_p=s.u_p, run_updates=s.run).label

    kw = {"table_facts": sizes["table_facts"], "unseen": sizes["unseen"], "synthetic": True}
    i64 = core.i64_seeds(cfg, test=True)  # the rehearsal reads its indexes with test-range seeds, never the registered 298001-298003
    a1 = planmod.build_items(core.STAGE_A1, specs, range(1, draws + 1), label_a1, lambda d: {**_mini_seed_a1(d - 1), "init_seed": init_a1}, cfg, checkpoint_root="s1", checkpoints_of=planmod.a1_checkpoints, i64_seeds=i64, **kw)
    a2 = planmod.build_items(core.STAGE_A2, specs, range(1, draws + 1), label_a2, lambda d: {**_mini_seed_a2(d - 1), "init_seed": init_a2}, cfg, checkpoint_root="a2", checkpoints_of=planmod.a2_checkpoints, i64_seeds=i64, **kw)
    bridge = {it["cell"]: {"arm": it["arm"], "facts": it["facts"], "slots": it["slots"], "draw": it["draw"], "init_seed": it["init_seed"], "u_p": it["u_p"], "run": it["run"], "seed_name": it["seed_name"], "seed_base": it["seed_base"], "table_facts": it["table_facts"], "unseen": it["unseen"], "snapshots": list(snapshots_of(next(sp for sp in specs if sp.name == it["cell_name"])))} for it in a2}
    draw_manifests: dict[str, dict[str, Any]] = {}
    for d in range(1, draws + 1):
        a1n, a2n = _mini_seed_a1(d - 1)["name"], _mini_seed_a2(d - 1)["name"]
        data, _ = items.load_data(ctx, {"seed_name": a2n, "seed_base": _mini_seed_a2(d - 1)["base"], **{k: kw[k] for k in ("table_facts", "unseen")}}, verify=False)
        draw_manifests[a1n] = {"path": made["manifests"][a1n], "sha256": file_sha256(Path(made["manifests"][a1n])), "groups": [core.STAGE_A1]}
        p2 = _write_manifest(root / "A2", a2n, data)
        draw_manifests[a2n] = {"path": str(p2), "sha256": file_sha256(p2), "groups": [core.STAGE_A2]}
    first = specs[0]
    tm_path = s1_root / "train.manifest.json"
    write_json(tm_path, {"tasks": [{"label": lab, "result_sha256": file_sha256(s1_root / "cells" / lab / "train.json")} for lab in made["cells"]]})
    train_manifest = {"path": str(tm_path), "sha256": file_sha256(tm_path)}
    extra = {
        "bridge_cells": bridge, "checkpoint_digests": digests_of(s1_root, a1), "draw_manifests": draw_manifests, "manifests": draw_manifests, "sizes": sizes, "synthetic": True, "context": {"dense": []},
        "plateau": {s.name: {"tree": [{"label": label_a1("T-OQ", s, d), "updates": sealed_available(s1_root, label_a1("T-OQ", s, d), s.run)} for d in range(1, draws + 1)], "flat": [{"label": label_a1("F-OQ", s, d), "updates": sealed_available(s1_root, label_a1("F-OQ", s, d), s.run)} for d in range(1, draws + 1)]} for s in specs},
        "identity_gate_cells": [[arm, first.facts, first.slots, 1, init_a1, first.u_p, first.run] for arm in ("F-OQ", "T-OQ")], "identity_seed_sets": {"1": _mini_seed_a1(0)}, "identity_gate_updates": list(snapshots_of(first)[:3]), "i64_seeds": i64,
        "p10s1_train_manifest": train_manifest, "p10s1_frozen_data_manifests": {n: r["sha256"] for n, r in draw_manifests.items() if core.STAGE_A1 in r["groups"]},
    }  # fmt: skip
    rec = planmod.build_plan(mode=planmod.REHEARSAL, cfg=cfg, repo=core.repo_root(), items={core.STAGE_A1: a1, core.STAGE_A2: a2}, run_dir=root, s1_run_dir=s1_root, extra=extra)
    path = root / "freeze" / "plan.json"
    core.write_record(path, rec)
    return Plan.load(path), ctx


def sealed_available(root: Path, label: str, limit: int) -> list[int]:
    from . import sealed

    return [u for u in sealed.available_updates(root, label) if u <= limit]


STAGE_ORDER = ("gates-a1", "a1", "gates-a2", "a2-train", "a2", "analysis", "report", "confirm")


item_errors = stages.item_errors


def run_pipeline(plan: Plan, ctx: items.Ctx, root: Path, *, repo: Path, workers: int, inline: bool, stages_to_run: tuple[str, ...] = STAGE_ORDER, adapter_identity: bool = True) -> dict[str, dict[str, Any]]:
    """Every stage of ``stages_to_run`` in order against the plan, through ``stages.execute_stage`` (the code path of the registered entry points; the registered preconditions are what a rehearsal does not
    have, by design: it has no freeze commit)."""
    out: dict[str, dict[str, Any]] = {}
    plan_path = root / "freeze" / "plan.json"
    for stage in stages_to_run:
        out[stage] = stages.execute_stage(stage, plan, ctx, root, plan_path, repo=repo, workers=workers, inline=inline, extra_worker_args=("--run-sealed",), run_checker=False, adapter_identity=adapter_identity)
    return out


def analysis_on_synthetic_registry(plan: Plan, root: Path, cfg: Any) -> dict[str, Any]:
    """Analysis, report and confirmation on a synthetic registry KEYED BY THE PLAN'S OWN LABELS (ruling 5): every row of sections 8.3 and 8.4 is reached somewhere, A1 and A2 are analysed with labels taken
    from the plan's items, R-CONFIRM is computed through A1's written record (JSON) as the ``confirm`` stage does, and the reports are rendered. Writes nothing; returns what it reached."""
    import json

    from . import analysis, report, synthetic

    out: dict[str, Any] = {}
    analyses: dict[str, Any] = {}
    for stage in (core.STAGE_A1, core.STAGE_A2):
        specs = stages._specs_of(plan, stage)
        label_of = analysis.label_of_from_items(plan.items(stage))
        seeds = plan.data.get("i64_seeds")
        reg = synthetic.full_registry(stage, synthetic.coverage_plan(specs), cfg, label_of, specs=specs, i64_seeds=seeds)
        analyses[stage] = analysis.analyze_stage(reg, stage, cfg, plateau=synthetic.plateau_series(cfg, specs=specs) if stage == core.STAGE_A1 else None, specs=specs, label_of=label_of, i64_seeds=seeds)
        rows = {r["row"] for c in analyses[stage]["cells"].values() for ck in c["checkpoints"].values() for comp in ("tree", "index") for r in ck[comp]["replicates"]}
        out[stage] = {"rows_reached": sorted(rows), "no_item_record": any("no item record" in r["reason"] for c in analyses[stage]["cells"].values() for ck in c["checkpoints"].values() for comp in ("tree", "index") for r in ck[comp]["replicates"])}
    a1_json = json.loads(json.dumps(analysis.public(analyses[core.STAGE_A1]), default=str))
    confirm = labels.r_confirm(labels.diagnosis_from_json(a1_json["r_diagnosis"]), analyses[core.STAGE_A2]["_diagnosis_object"])
    full = analysis.analyze_all(analyses[core.STAGE_A1], analyses[core.STAGE_A2])
    text = report.render(json.loads(json.dumps(full, default=str)))
    out["r_confirm"] = {k: v["value"] for k, v in confirm.items()}
    out["report_chars"] = len(text)
    out["status"] = "COMPLETE" if not any(out[s_]["no_item_record"] for s_ in (core.STAGE_A1, core.STAGE_A2)) else "FAILED"
    return out


def run_candidate(root: Path, *, repo: Path, plan_path: Path | None = None) -> dict[str, Any]:
    """The candidate phase (ruling 5): every stage rehearsed against the CANDIDATE ``freeze/plan.json`` itself, without reading a registered checkpoint or a sealed value. It enumerates, for every stage, the
    tasks, the items, the labels, the checkpoint and manifest paths, the digests, the bridge cells and the seeds; verifies the plan's identities (frozen files, config, manifests, the items against a
    re-derivation); runs the analysis, the report and the confirmation on a synthetic registry keyed by the plan's own labels; and records the plan file's SHA-256."""
    from . import adapter

    cfg = core.load_config(repo / core.CONFIG)
    path = plan_path or repo / core.PLAN
    plan_sha = file_sha256(path)  # hashed when the file is loaded and used throughout (audit N4); compared again at the end
    plan = Plan.load(path)
    problems: list[str] = []
    if plan.mode != planmod.REGISTERED:
        raise planmod.StageRefused("refused: the candidate phase rehearses a registered plan")
    run_dir = Path(plan.data["run_dir"])
    try:
        planmod.verify_plan(plan, repo, run_dir, check_items=True, candidate=True)
    except planmod.StageRefused as exc:
        problems.append(str(exc))
    counts: dict[str, int] = {}
    for stage in ("a1", "a2-train", "a2"):
        tasks = stages.make_tasks(stage, plan, run_dir, path, None, ())  # type: ignore[arg-type]
        labels_ = [t.label for t in tasks]
        counts[stage] = len(tasks)
        if len(set(labels_)) != len(labels_) or not tasks:
            problems.append(f"{stage}: task labels are empty or not unique")
    n_a1 = len(plan.items(core.STAGE_A1))
    n_a2 = len(plan.items(core.STAGE_A2))
    if (n_a1, n_a2) != (280, 40) or counts != {"a1": 70, "a2-train": 20, "a2": 20}:
        problems.append(f"the plan lists {n_a1} A1 items and {n_a2} A2 items in {counts} tasks; the registered plan has 280 and 40 in 70, 20 and 20")
    s1_run = Path(plan.data["s1_run_dir"])
    digests = plan.data.get("checkpoint_digests") or {}
    for it in plan.items(core.STAGE_A1):
        snap = s1_run / "cells" / it["cell"] / "snapshots" / s1core.snapshot_stem(it["update"]) / "model.pt"
        if not snap.is_file() or f"{it['cell']}|{it['update']}" not in digests:
            problems.append(f"{it['id']}: checkpoint file or digest missing")
        s1core.parse_label(it["cell"])
    for label, spec in (plan.data.get("bridge_cells") or {}).items():
        try:
            adapter.assert_seed_allowed(planmod.REGISTERED, spec, cfg)
        except ValueError as exc:
            problems.append(str(exc))
        if not {spec["u_p"], spec["run"]} <= set(spec["snapshots"]):
            problems.append(f"{label}: the snapshot schedule lacks U_P or the run length")
    for name, rec in (plan.data.get("draw_manifests") or {}).items():
        if not Path(rec["path"]).is_file():
            problems.append(f"manifest {name} is missing")
    synth = analysis_on_synthetic_registry(plan, root, cfg)
    if synth["status"] != "COMPLETE":
        problems.append("the analysis on the synthetic registry did not find every record by the plan's labels")
    if file_sha256(path) != plan_sha:
        problems.append("the plan file changed while the candidate phase ran")
    return {"status": "COMPLETE" if not problems else "INCOMPLETE", "plan_file_sha256": plan_sha, "plan_path": str(path), "tasks": counts, "items": {"A1": n_a1, "A2": n_a2}, "problems": problems, "synthetic_registry": synth}


def run_synthetic(root: Path, *, draws: int, repo: Path, inline: bool = True, workers: int = 1) -> dict[str, Any]:
    """The synthetic phase. Returns the stage manifests."""
    cfg = core.load_config()
    from studies.p10s1 import train as t

    t.configure()
    plan, ctx = build_synthetic_plan(root, cfg, draws)
    manifests = run_pipeline(plan, ctx, root, repo=repo, workers=workers, inline=inline)
    synth = analysis_on_synthetic_registry(plan, root, cfg)
    return {"stages": {s: {"status": m["status"], "charged_seconds": m["charged_seconds"]} for s, m in manifests.items()}, "plan_sha256": plan.sha256(), "synthetic_registry": synth, "item_errors": item_errors(root)}


# --- the real-size phase ---------------------------------------------------------------------------------------------------------------------------------------
def build_real_plan(root: Path, cfg: Any, repo: Path, *, synthetic: bool = False, seeds: Any = None, init: int | None = None, sizes: dict[str, int] | None = None) -> tuple[Plan, items.Ctx]:
    """One T-OQ and one F-OQ cell at 32,768 facts and 16,384 slots of the rehearsal draw (299201, initialisation 330692), trained through the adapter for 64 updates; its own plan. ``synthetic``, ``seeds``,
    ``init`` and ``sizes`` exist for the unit test, which runs this code path at tiny sizes on the test seeds with a random backbone; the rehearsal proper passes none of them."""
    from studies.p10s1 import core as s1

    r = cfg["rehearsal"]
    spec = core.CellSpec(int(r["facts"]), int(r["slots"]), "primary", int(r["snapshots"][0]), int(r["snapshots"][1]), (int(r["snapshots"][0]), int(r["snapshots"][1])))
    seeds = seeds or core.rehearsal_seeds(cfg)
    init = int(cfg["seeds"]["rehearsal_init"]) if init is None else init
    sz = sizes or {"table_facts": s1.FACT_TABLE, "unseen": s1.UNSEEN_FACTS}
    root.mkdir(parents=True, exist_ok=True)
    ctx = items.Ctx("rehearsal", root, root / "s1", None if synthetic else freeze.experiments_root(), synthetic=synthetic, run_sealed=True, sizes=sz, index_seeds=core.i64_seeds(cfg, test=True))
    s1_root = root / "s1"
    data, _ = items.load_data(ctx, {"seed_name": seeds.name, "seed_base": seeds.facts, "table_facts": sz["table_facts"], "unseen": sz["unseen"]}, verify=False)
    manifest = _write_manifest(s1_root, seeds.name, data)
    bb = items.backbone_of(ctx)
    for arm in ("T-OQ", "F-OQ"):
        cell = s1.make_cell("P", arm, spec.facts, spec.slots, 1, init, u_p=spec.u_p, run_updates=spec.run)
        folder = s1_root / "cells" / cell.label
        job = adapter.job_for(cell, data, seeds, bb, folder, list(r["snapshots"]))
        res = adapter.run_cell(job)
        s1.write_record(folder / "train.json", {**s1.envelope("train"), "label": cell.label, "snapshot_sha256": res["snapshot_sha256"]})
        s1eval.evaluate_cell(cell, s1_root, data, bb, readouts=[int(x) for x in r["snapshots"]], deep_at=cell.u_p, r1_seed=seeds.r1_codes, hash_seed=s1.h8_seed(seeds), rows=None, require_train_record=True)

    def label(arm: str, s: core.CellSpec, d: int) -> str:
        return s1.make_cell("P", arm, s.facts, s.slots, d, init, u_p=s.u_p, run_updates=s.run).label

    seed = {"name": seeds.name, "base": seeds.facts, "init_seed": init}
    kw = {"table_facts": sz["table_facts"], "unseen": sz["unseen"], "synthetic": synthetic}
    a1 = planmod.build_items(core.STAGE_A1, [spec], [1], label, lambda d: seed, cfg, checkpoint_root="s1", checkpoints_of=planmod.a2_checkpoints, i64_seeds=core.i64_seeds(cfg, test=True), **kw)
    a2 = planmod.build_items(core.STAGE_A2, [spec], [1], label, lambda d: seed, cfg, checkpoint_root="a2", checkpoints_of=planmod.a2_checkpoints, i64_seeds=core.i64_seeds(cfg, test=True), **kw)
    bridge = {it["cell"]: {"arm": it["arm"], "facts": it["facts"], "slots": it["slots"], "draw": 1, "init_seed": init, "u_p": it["u_p"], "run": it["run"], "seed_name": seeds.name, "seed_base": seeds.facts, "table_facts": it["table_facts"], "unseen": it["unseen"], "snapshots": [int(x) for x in r["snapshots"]]} for it in a2}
    dm = {seeds.name: {"path": str(manifest), "sha256": file_sha256(manifest), "groups": [core.STAGE_A1, core.STAGE_A2]}}
    extra = {"bridge_cells": bridge, "checkpoint_digests": digests_of(s1_root, a1), "draw_manifests": dm, "manifests": dm, "sizes": sz, "synthetic": synthetic, "context": {"dense": []}, "plateau": {}}
    rec = planmod.build_plan(mode=planmod.REHEARSAL, cfg=cfg, repo=repo, items={core.STAGE_A1: a1, core.STAGE_A2: a2}, run_dir=root, s1_run_dir=s1_root, extra=extra)
    path = root / "freeze" / "plan.json"
    core.write_record(path, rec)
    return Plan.load(path), ctx


def run_real(root: Path, *, repo: Path, workers: int, inline: bool = False, cfg: Any = None, **plan_kw: Any) -> dict[str, Any]:
    cfg = cfg or core.load_config()
    s1train.configure()
    plan, ctx = build_real_plan(root, cfg, repo, **plan_kw)
    run = run_pipeline(plan, ctx, root, repo=repo, workers=workers, inline=inline, stages_to_run=("gates-a1", "a1", "gates-a2", "a2-train", "a2"), adapter_identity=False)
    seconds_per_read: dict[str, float] = {}
    for stage in ("A1", "A2"):
        for p in sorted((root / stage).glob("items/*/read.*.json")) if (root / stage).is_dir() else []:
            rec = core.read_record(p, "read")
            seconds_per_read[f"{stage}|{rec['cell']}|u{rec['update']}|{rec['read']}"] = float(rec["seconds"])
    peaks = {s: max((float(t.get("peak_rss_bytes", 0)) for t in m["tasks"].values()), default=0.0) for s, m in run.items()}
    return {"stages": {s: {"status": m["status"], "charged_seconds": m["charged_seconds"]} for s, m in run.items()}, "seconds_per_read": seconds_per_read, "peak_rss_bytes_by_stage": peaks, "facts": cfg["rehearsal"]["facts"], "slots": cfg["rehearsal"]["slots"], "plan_sha256": plan.sha256(), "item_errors": item_errors(root)}


# --- gates 1 and 2 on the registered checkpoints -----------------------------------------------------------------------------------------------------------------
def run_gates12(root: Path, s1_run_dir: Path, *, repo: Path, workers: int, plan_items: list[dict[str, Any]] | None = None, synthetic: bool = False, sizes: dict[str, int] | None = None, draw_names: list[str] | None = None, identity: dict[str, Any] | None = None) -> dict[str, Any]:
    """Gate 1 and gate 2 on every registered A1 checkpoint (items from the config: the freeze does not exist yet) through the worker pool, and the adapter identity gate on P10-S1's draw-1 cells. Gate 3 is not run.
    The keyword arguments exist for the unit test, which runs this code path on the synthetic miniature run."""
    cfg = core.load_config()
    s1train.configure()
    itemset = plan_items if plan_items is not None else planmod.registered_items(cfg)[core.STAGE_A1]
    sz = sizes or {"table_facts": s1core.FACT_TABLE, "unseen": s1core.UNSEEN_FACTS}
    names = draw_names or [f"p10s1-draw-{d}" for d in range(1, 6)]
    draw_manifests = {n: {"path": str(s1_run_dir / "draws" / n / "data_manifest.json"), "sha256": file_sha256(s1_run_dir / "draws" / n / "data_manifest.json"), "groups": [core.STAGE_A1]} for n in names}
    rec = planmod.build_plan(
        mode=planmod.REHEARSAL, cfg=cfg, repo=repo, items={core.STAGE_A1: itemset, core.STAGE_A2: []}, run_dir=root, s1_run_dir=s1_run_dir,
        extra={"sizes": sz, "synthetic": synthetic, "draw_manifests": draw_manifests, "manifests": draw_manifests},
    )  # fmt: skip
    path = root / "freeze" / "plan.json"
    core.write_record(path, rec)
    plan = Plan.load(path)
    ctx = stages.ctx_for(plan, root, run_sealed=False, experiments_root=None if synthetic else freeze.experiments_root())
    began = time.monotonic()
    tasks = []
    for label in stages.labels_of_stage(plan, "a1"):
        argv = (sys.executable, "-m", "studies.p10ir.stages", "work", "gates12", "--stage", "a1", "--labels", label, "--run-dir", str(root), "--plan", str(path), "--mode", planmod.REHEARSAL)
        tasks.append(runner.Task(label, argv, root / "gates12" / "tasks" / f"{safe_name(label)}.done.json", root / "gates12" / "tasks" / f"{safe_name(label)}.failed.json", root / "gates12" / "tasks" / f"{safe_name(label)}.log"))
    ledger_path = root.parent / f"P10IR-rehearsal-{root.name}-ledger.json"
    planmod.require_ignored_path(repo, ledger_path)
    ledger = core.Ledger(ledger_path, plan.total_cap_seconds())
    if workers < 1:
        outcomes = {}
        for t in tasks:
            stages.work_gates12(ctx, plan, [t.label])
            outcomes[t.label] = {"status": runner.COMPLETED}
    else:
        outcomes, _ = runner.run_tasks(tasks, workers=workers, cap_seconds=ledger.remaining(), rss_worker_bytes=int(cfg["resources"]["rss_worker_bytes"]), rss_aggregate_bytes=int(cfg["resources"]["rss_aggregate_bytes"]), env={"PYTHONPATH": str(repo)})
    results = [core.read_record(p, "gate")["gate"] for p in sorted((root / "gates12" / "items").glob("*.json"))]
    ok1 = bool(results) and len(results) == len(itemset) and all(r["identity"]["passed"] is True for r in results)
    ok2 = bool(results) and len(results) == len(itemset) and all(r["passed"] is True for r in results)
    cfg_s = cfg["seeds"]
    cells = [(arm, int(cfg_s["identity_gate_cell"][0]), int(cfg_s["identity_gate_cell"][1]), int(cfg_s["identity_gate_draw"]), int(cfg_s["p10s1_init_base"]) + int(cfg_s["identity_gate_draw"]), 8192, 49152) for arm in ("F-OQ", "T-OQ")]
    ident_kw: dict[str, Any] = {"cells": cells, "seeds_of": core.p10s1_draw_seeds, "updates": [int(u) for u in cfg_s["identity_gate_updates"]]}
    ident_kw.update(identity or {})
    ident = adapter.identity_gate(ctx, root / "gates12" / "identity_work", cfg=cfg, **ident_kw)
    seconds = time.monotonic() - began
    ledger.charge("gates12", root.name, seconds)
    return {
        "gate1_passed": ok1, "gate2_passed": ok2, "gate3_run": False, "items_expected": len(itemset), "items_done": len(results), "task_statuses": {k: v["status"] for k, v in outcomes.items()},
        "adapter_identity": {"passed": ident.get("passed"), "status": ident.get("status")}, "charged_seconds": seconds,
    }  # fmt: skip


# --- command -----------------------------------------------------------------------------------------------------------------------------------------------------
def cmd_rehearse(args: argparse.Namespace) -> int:
    repo = Path(args.repo) if args.repo else core.repo_root()
    root = Path(args.run_dir)
    if root.exists() and any(root.iterdir()):
        raise planmod.StageRefused(f"refused: {root} exists and is not empty; a rehearsal runs in a new directory")
    root.mkdir(parents=True, exist_ok=True)
    phases = [p for p in args.phases.split(",") if p]
    record: dict[str, Any] = {**core.envelope("rehearsal"), "phases": phases, "caps_provisional": core.caps_provisional(core.load_config(repo / core.CONFIG)), "platform": gates.platform_record(), "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "stages": {}}
    statuses: dict[str, list[str]] = {}
    for phase in phases:
        if phase == "synthetic":
            res = run_synthetic(root / "synthetic", draws=args.draws, repo=repo)
            record["synthetic"] = res
        elif phase == "real":
            res = run_real(root / "real", repo=repo, workers=args.workers)
            record["real"] = res
        elif phase == "candidate":
            record["candidate"] = run_candidate(root / "candidate", repo=repo, plan_path=Path(args.candidate_plan) if getattr(args, "candidate_plan", None) else None)
            continue
        elif phase == "gates12":
            if not args.s1_run_dir:
                raise planmod.StageRefused("refused: gates12 needs --s1-run-dir")
            res = run_gates12(root / "gates12", Path(args.s1_run_dir), repo=repo, workers=args.workers)
            record["registered_checkpoint_gates"] = res
            continue
        else:
            raise planmod.StageRefused(f"refused: unknown phase {phase!r}")
        for s, m in res["stages"].items():
            statuses.setdefault(s, []).append("INCOMPLETE" if res.get("item_errors") and s in ("a1", "a2") else m["status"])
    for s in stages.REHEARSAL_STAGES:
        have = statuses.get(s, [])
        record["stages"][s] = {"status": "COMPLETE" if have and all(x == "COMPLETE" for x in have) and len(have) == sum(1 for p in phases if p in ("synthetic", "real") and (p == "synthetic" or s in ("gates-a1", "a1", "gates-a2", "a2-train", "a2"))) else "INCOMPLETE", "phases": have}
    core.write_record(root / "rehearsal.json", record)
    print(json.dumps({"rehearsal": str(root / "rehearsal.json"), "sha256": file_sha256(root / "rehearsal.json"), "stages": {k: v["status"] for k, v in record["stages"].items()}}))
    return 0
