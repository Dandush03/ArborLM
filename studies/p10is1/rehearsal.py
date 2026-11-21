# ruff: noqa: E501
"""P10IS1 rehearsals (ADR-0024 sections 8.1, 11, 17.1, 18). Two rehearsals, never one: a MEASURING rehearsal on provisional caps (it measures seconds per update, the contention ratio, evaluation seconds per snapshot
with DEP at every snapshot, and the peak memory; it cannot be frozen on) and, after the projection has written the granted lengths and the caps into the candidate plan, a COUNTING rehearsal of every registered stage end to
end against that exact file, whose SHA-256 goes into the rehearsal record. Both use the rehearsal draw only, with the analysis and the report run on a synthetic registry keyed by the plan's labels.

This module holds: the tiny synthetic pipeline (``run_synthetic``: every training, ladder, evaluation, baseline, timing and throughput stage of the plan format on a tiny memory with test seeds, a random backbone, one process),
the counting rehearsal of a candidate plan file (``run_candidate``: every stage's items derived from the plan only and checked against it, the analysis and the report on a synthetic registry keyed by the plan's labels), the R2
qualification table of the reference (``qualification_table``: a DEP condition R2 fails at a fraction of U_P on any view is not used at that fraction for any arm of that row, NOT QUALIFIED AT that fraction), and the record.
The real-size measuring rehearsal is the lead's run (``rehearse --real`` is not implemented in this module); nothing here trains at a registered size.
"""

import argparse
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from arborlm.io import file_sha256, read_json

from . import analysis, core, items, report, stages, synthetic
from . import labels as L
from . import plan as planmod

TINY_FACTS = 128


def tiny_config_text(base: Path | None = None) -> str:
    """The real config's text with the ladder shrunk to tiny sizes (32 x {1, 1.5, 2, 3, ...}) and the timing repeats cut, for the synthetic pipeline only. Thresholds are untouched."""
    text = (base or core.repo_root() / core.CONFIG).read_text(encoding="utf-8")
    for old, new in (("base = 65536\n", "base = 32\n"), ("half_unit = 32768\n", "half_unit = 16\n"), ("doubling_from = 512\n", "doubling_from = 4\n"), ("timing_warmup_updates = 32\n", "timing_warmup_updates = 2\n"), ("timing_updates = 256\n", "timing_updates = 4\n"), ("timing_repeats = 3\n", "timing_repeats = 1\n")):
        if old not in text:
            raise ValueError(f"the config lacks the line {old!r}")
        text = text.replace(old, new)
    return text


def tiny_cells(cfg: Mapping[str, Any], draws: Sequence[int] = (1, 2)) -> tuple[list[dict[str, Any]], core.PlanParams]:
    """A tiny plan's cells: one ladder cell (128 facts, 1,024 slots; F-OQ, T-OQ, H8, D-OQ; U0 = 48, G = 192 = 4 x U0) and a non-ladder cell (128 facts, 4,096 slots; F-OQ, D-OQ, R2), test seeds."""
    u0, granted = 48, 192
    name = core.cell_name(TINY_FACTS, 1024)
    params = core.PlanParams({2048: 8, 8192: 8, 32768: 8, TINY_FACTS: 8}, {}, {name: u0}, {name: granted}, True)
    out = []
    for d in draws:
        seeds, init = core.seeds_for(core.TEST, d, cfg)
        for arm, slots, ladder in (("F-OQ", 1024, True), ("T-OQ", 1024, True), ("H8", 1024, True), ("D-OQ", 1024, True), ("F-OQ", 4096, False), ("D-OQ", 4096, False), ("R2", 4096, False)):
            run = granted if ladder else (8 if arm == "R2" else 48)
            lr = 0.003
            cell = core.make_cell(core.TEST, arm, TINY_FACTS, slots, d, init, u_p=8, run=run, lr=lr)
            snaps = core.loaded_snapshots(8, granted, cfg, doubling=[4, 8, 16]) if ladder else core.grid_snapshots(8, run, cfg)
            out.append({"label": cell.label, "arm": arm, "facts": TINY_FACTS, "slots": slots, "draw": d, "init_seed": init, "seed_name": seeds.name, "seed_base": seeds.facts, "u_p": 8, "lr": lr, "run": run, "ladder_cell": ladder, "u0": u0 if ladder else None, "snapshots": snaps, "unit": f"{arm}|{slots}", "mode": core.TEST})
    return out, params


def tiny_plan(root: Path, repo: Path, cfg_path: Path) -> planmod.Plan:
    """A plan of the plan format on tiny cells (mode test): the real plan's frozen-file hashes, the tiny cells and parameters."""
    cfg = core.load_config(cfg_path)
    cells, params = tiny_cells(cfg)
    data = planmod.build_plan(mode=core.TEST, cfg=cfg, repo=repo, params=core.PlanParams({2048: 8, 8192: 8, 32768: 16}, {u: 0.003 for u in core.units(cfg)}, {"2K/256": 98304, "8K/1K": 98304, "32K/4K": 98304}, {"2K/256": 98304, "8K/1K": 98304, "32K/4K": 98304}), run_dir=root / "run", extra={"sizes": {"table_facts": 512, "unseen": 64}})
    data["cells"], data["params"] = cells, params.to_json()
    data["params"]["rates"] = {}
    data["frozen_files"] = planmod.frozen_file_hashes(repo)
    data["stage_caps"] = {k: float(v) for k, v in cfg["caps"].items() if k.endswith("_hours")}
    data["caps_provisional"] = False
    data["calibration"] = {"h8": {"undertrained_cells": [], "calibrated_cells": []}, "sat256": True}
    pl = root / "plan.json"
    core.write_record(pl, data, overwrite=True)
    return planmod.Plan.load(pl)


def run_synthetic(root: Path, *, repo: Path, workers: int = 1) -> dict[str, Any]:
    """The whole stage chain on tiny cells, inline: gates -> timing -> train (to U0) -> ladder (whole-cell rounds up to G) -> evaluate -> baselines -> throughput. Every stage's items come from the plan file. The analysis is
    not run on these records (a tiny plan is not the registry); the candidate rehearsal runs it on a synthetic registry keyed by the real plan's labels."""
    root.mkdir(parents=True, exist_ok=True)
    cfg_path = root / "tiny_config.toml"
    cfg_path.write_text(tiny_config_text(), encoding="utf-8")
    pl = tiny_plan(root, repo, cfg_path)
    run_dir = root / "run"
    ctx = items.Ctx(core.TEST, run_dir, None, synthetic=True, sizes={"table_facts": 512, "unseen": 64}, config_path=cfg_path)
    args = argparse.Namespace(freeze_commit=None, synthetic=True)
    always_quiet = {"quiet": True, "load_average": 0.1, "other_study_processes": []}
    stages_done: dict[str, Any] = {}
    for stage in ("gates", "timing", "train", "ladder", "evaluate", "baselines", "throughput"):
        rec = stages.execute_stage(stage, pl, ctx, run_dir, pl.path or root / "plan.json", args, repo=repo, inline=True, workers=workers, quiet_reading=lambda: always_quiet, end_fn=lambda s: {"ok": True, "other_study_processes": []}, sleep=lambda s: None)
        stages_done[stage] = {"status": rec["status"], "result": core.jsonable(rec.get("result"))}
        if rec["status"] != "COMPLETE":
            break
    return {"stages": stages_done, "plan": str(pl.path), "run_dir": str(run_dir), "cells": len(pl.data["cells"]), "ladder": {n: read_json(stages.ladder_path(run_dir, n))["u_run"] for n in items.cell_names_of(pl.data["cells"])}}


def check_plan_items(pl: planmod.Plan) -> dict[str, Any]:
    """Every registered stage's items derived from the plan file only, each checked against the plan: every item's cell is a cell of the plan, the training items cover every cell, the ladder items every ladder cell, the evaluation
    items every cell that is not a ladder cell, the baselines every (draw, row) read, the timing items every (arm, slots) the plan trains, the throughput items only cells the plan trains."""
    labels = {c["label"] for c in pl.data["cells"]}
    problems: list[str] = []
    counts: dict[str, int] = {}
    for stage in planmod.STAGES:
        its = pl.items(stage)
        counts[stage] = len(its)
        for it in its:
            for lab in ([it["cell"]] if "cell" in it else list(it.get("labels", []))):
                if lab not in labels:
                    problems.append(f"{stage}: {it['id']} names {lab}, which the plan does not run")
    tr = {i["cell"] for i in pl.items("train")}
    if tr != labels:
        problems.append("the training items do not cover exactly the plan's cells")
    ladder = {lab for i in pl.items("ladder") for lab in i["labels"]}
    if ladder != {c["label"] for c in pl.data["cells"] if c["ladder_cell"]}:
        problems.append("the ladder items do not cover exactly the plan's ladder cells")
    if {i["cell"] for i in pl.items("evaluate")} != {c["label"] for c in pl.data["cells"] if not c["ladder_cell"]}:
        problems.append("the evaluation items do not cover exactly the plan's cells that are not ladder cells")
    if {(i["arm"], i["slots"]) for i in pl.items("timing")} != {(c["arm"], c["slots"]) for c in pl.data["cells"]}:
        problems.append("the timing items are not exactly the (arm, slots) the plan trains")
    for i in pl.items("throughput"):
        c = pl.cell(i["cell"])
        if (c["facts"], c["slots"]) != (i["facts"], i["slots"]):
            problems.append(f"throughput item {i['id']} does not match its cell")
    return {"counts": counts, "problems": problems, "passed": not problems}


def qualification_table(r2: Mapping[tuple[int, str], Mapping[int, Mapping[str, L.Obs]]], u_p_by_row: Mapping[int, int], cfg: Mapping[str, Any] | None = None) -> dict[str, dict[str, list[str]]]:
    """The reference qualification (section 8.1): ``r2[(row, view)][update][panel]`` for R2 at the row's reference cell on the rehearsal and both calibration draws, at every snapshot fraction of U_P. A condition that R2
    fails at a fraction on ANY view is not qualified at that fraction (for any arm of that row); a condition stays qualified where R2 is under the a_use floor (DEP does not apply there). Returns row -> fraction key ->
    qualified conditions (a fraction at which every condition holds is listed with all three)."""
    out: dict[str, dict[str, list[str]]] = {}
    for (row, _view), series in r2.items():
        u_p = int(u_p_by_row[row])
        for update, panels in series.items():
            key = analysis.fraction_key(update, u_p)
            slot = out.setdefault(str(row), {}).setdefault(key, list(L.DEP_CONDITIONS))
            for obs in panels.values():
                for failed in L.dep_failures(obs, memory=True, qualified=set(L.DEP_CONDITIONS)):
                    if failed in slot:
                        slot.remove(failed)
    return out


def run_candidate(plan_path: Path, run_dir: Path, *, repo: Path) -> dict[str, Any]:
    """The counting rehearsal's part against the candidate plan FILE: every stage's items derived from the plan and checked against it; the analysis and the report on a synthetic registry keyed by the plan's labels. Its record
    names the SHA-256 of the file."""
    pl = planmod.Plan.load(plan_path)
    chk = check_plan_items(pl)
    params = pl.params()
    reg = synthetic.build(params, cells=pl.data["cells"], u_run={n: int(params.u0[n]) for n in params.u0})
    res = analysis.analyze(reg)
    text = report.render(res, throughput={"state": "PAUSED"}, caps=pl.data["stage_caps"]) if res["status"] == "COMPLETE" else ""
    ok = chk["passed"] and res["status"] == "COMPLETE" and bool(text)
    return {"status": "COMPLETE" if ok else "FAILED", "plan_file_sha256": file_sha256(plan_path), "item_counts": chk["counts"], "item_problems": chk["problems"], "analysis_lines": res.get("lines"), "report_chars": len(text), "synthetic_registry_reads": len(reg.reads)}


def cmd_rehearse(args: argparse.Namespace) -> int:
    """The synthetic rehearsal (tiny sizes, test seeds, a random backbone, one process): the stage chain end to end. The real-size measuring and counting rehearsals are the lead's runs."""
    repo = Path(args.repo) if args.repo else core.repo_root()
    root = Path(args.run_dir)
    if root.exists() and any(root.iterdir()):
        raise core.StageRefused(f"refused: {root} is not a new rehearsal directory")
    planmod.require_ignored_run_dir(repo, root)
    rec = run_synthetic(root, repo=repo)
    ok = all(v["status"] == "COMPLETE" for v in rec["stages"].values())
    print(json.dumps({"synthetic": {k: v["status"] for k, v in rec["stages"].items()}, "ladder_u_run": rec["ladder"], "passed": ok}))
    return 0 if ok else 1

