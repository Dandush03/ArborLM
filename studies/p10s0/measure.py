# ruff: noqa: E501
"""P10S0 measurement of the wall time of one ``analysis`` and one ``report`` on synthetic FULL-registry records at real record sizes (the pre-freeze audit's request; README step 8).

``uv run --locked python -m studies.p10s0.stages measure-analysis --out <record.json> [--out-root <dir>]`` builds, in a temporary directory, a run directory with the records of the whole registry (all 230
Q1 cells, the WX and probe cells of the candidate A5-D) whose layout is copied from one tiny real cell trained and evaluated here on test seeds (so the keys are the code's own, never hand-copied): per learned
cell an ``updates.jsonl`` of the cell type's real number of lines, a ``diagnostics.jsonl`` every 64 updates, ``train.json`` and one ``eval.json`` per readout; with a few missing cells, one failed cell, one non-finite
value and a replaced draw. It then times the real workers (``work analyze``, ``work report``) as subprocesses (start-up, imports, reading, computing and writing included, as the registered stage tasks pay them),
and, in process, the analysis and the report of synthetic registries that reach several outcome rows, missing cells, non-finite values, failed gates and each cut. The record it writes holds both times; the
analysis time recommended for ``caps --analysis-wall-seconds`` is the stage time plus the largest in-process analysis time over the rows (the computation counted twice, so the figure only errs high).

Uses test seeds (920001+) and synthetic records only; takes no registered, rehearsal or check input; every number it writes is MEASURED wall seconds on this machine and a statement about nothing else.
The records at real size take disk (about 3 GB; ``expected_bytes`` is printed first) and are deleted at the end unless ``--keep``. ``--tiny`` writes the same registry at the DRY unit (8 updates; for tests):
its times are not for the caps and the record says so.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from . import analysis, arm_selection, core, report
from . import synthetic as syn

TINY_UNIT = 8
DIAG_EVERY_REAL = core.DIAG_EVERY
DIAG_EVERY_TINY = 2
CANDIDATE = "A5-D"
MISSING_LABELS = 3  # leave out this many learned cells
SEED_BASE = 920001  # the one seed used here, for the template cell's data (a test seed)


class MeasureError(RuntimeError):
    pass


def make_template(work: Path, unit: int) -> dict[str, Any]:
    """Train and evaluate one tiny A5-D cell on test seeds and return its records (update line, diagnostics line, train record, eval record) as the layout of every synthetic cell."""
    import torch  # noqa: F401

    from studies.p9 import controls

    from . import evaluate, train

    train.configure()
    spec = core.test_set(2)
    draw = syn.tiny_data(spec, 2048)
    backbone = controls.synthetic_backbone()
    cell = core.make_cell("A5-D", "2K/4K", "Q1", 1, 0)
    out = work / "template" / "cell"
    job = train.Job(cell=cell, mode="dry", data=draw, stream=train.training_stream_for(draw, 128), backbone=backbone, out_dir=out, init_seed=920041, r1_seed=draw.seeds.r1_codes, target_seed=spec.target_seed("2K/4K", 0), hyper=core.HYPER._replace(u_pre=4.0), unit=8, diag_every=4, max_updates=8, snapshots=(8,))
    train.run_job(job)
    run_dir = work / "template"
    dest = core.cell_dir(run_dir, cell.label)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(out, dest)
    rows = evaluate.corpus_rows(syn.tiny_corpus())[:64]
    evaluate.evaluate_cell(cell, run_dir, draw, backbone, facts=128, readouts=[8], init_seed=920041, r1_seed=draw.seeds.r1_codes, rows=rows, target_seed=spec.target_seed("2K/4K", 0), swap_seed=spec.swap_seed(2048), require_train_record=True)
    return {
        "update": json.loads((out / "updates.jsonl").read_text().splitlines()[0]), "diagnostics": json.loads((out / "diagnostics.jsonl").read_text().splitlines()[0]),
        "train": json.loads((out / "train.json").read_text()), "eval": json.loads(core.eval_path(run_dir, cell.label, 8).read_text()),
    }  # fmt: skip


def accuracy_of(cell: core.Cell) -> float:
    """A fixed, deterministic pattern of values (not a result): A0 fails at 2K/4K on draws 1-6 and at 8K/16K on draws 1-3, every other cell succeeds."""
    if cell.arm == "A0" and ((cell.celltype == "2K/4K" and cell.draw <= 6) or (cell.celltype == "8K/16K" and cell.draw <= 3)):
        return 0.05
    return 0.97


def write_eval(template: dict[str, Any], cell: core.Cell, run_dir: Path, update: int, *, nan: bool) -> None:
    rec = json.loads(json.dumps(template["eval"]))
    acc = accuracy_of(cell)
    for panel in ("A", "B"):
        rec["panels"][panel]["accuracy"] = acc
        rec["read_swap"][panel]["a_use"] = acc
    for k in ("H1", "H2"):
        rec["secondary"][k]["accuracy"] = acc
    rec.update({"label": cell.label, "arm": cell.arm, "celltype": cell.celltype, "block": cell.block, "draw": cell.draw, "seed_index": cell.seed_index, "slots": cell.slots, "facts": cell.facts, "update": update})
    if nan:
        rec["panels"]["A"]["accuracy"] = float("nan")
    path = core.eval_path(run_dir, cell.label, update)
    path.parent.mkdir(parents=True, exist_ok=True)
    core.write_record(path, core.jsonable(rec))


def write_cell(template: dict[str, Any], cell: core.Cell, run_dir: Path, unit: int, diag_every: int, *, failed: bool, nan: bool) -> int:
    """One cell's records; returns the bytes written. Logs only for learned cells (the analysis reads no other)."""
    folder = core.cell_dir(run_dir, cell.label)
    folder.mkdir(parents=True, exist_ok=True)
    total = cell.ct.updates(unit)
    rec = json.loads(json.dumps(template["train"]))
    rec.update({"label": cell.label, "arm": cell.arm, "celltype": cell.celltype, "block": cell.block, "draw": cell.draw, "seed_index": cell.seed_index, "slots": cell.slots, "facts": cell.facts, "status": "failed" if failed else "completed", "matched_updates": total, "run_updates": total})
    rec["schedule"] = {**rec["schedule"], "u_pre": int(core.schedule_for(cell.arm, cell.celltype, core.HYPER, unit).u_pre or 0) if cell.base == "A2" else rec["schedule"].get("u_pre")}
    core.write_record(folder / "train.json", rec)
    size = (folder / "train.json").stat().st_size
    if cell.learned:
        line = json.dumps(template["update"], sort_keys=True)
        prefix = line[: line.rindex('"update"')] + '"update": '
        with (folder / "updates.jsonl").open("w", encoding="utf-8") as stream:
            stream.write("".join(f"{prefix}{n}}}\n" for n in range(1, total + 1)))
        with (folder / "diagnostics.jsonl").open("w", encoding="utf-8") as stream:
            for n in range(diag_every, total + 1, diag_every):
                stream.write(json.dumps({**template["diagnostics"], "update": n}, sort_keys=True) + "\n")
        size += (folder / "updates.jsonl").stat().st_size + (folder / "diagnostics.jsonl").stat().st_size
    if not failed:
        for u in cell.ct.readout_updates(unit):
            write_eval(template, cell, run_dir, u, nan=nan)
            size += core.eval_path(run_dir, cell.label, u).stat().st_size
    return size


def expected_bytes(template: dict[str, Any], unit: int) -> int:
    """About how much disk the registry takes (an estimate from the template's line sizes)."""
    cells = [*core.q1_cells(False), *core.wx_cells(CANDIDATE), *core.probe_cells(CANDIDATE)]
    update_line = len(json.dumps(template["update"], sort_keys=True)) + 4
    diag_line = len(json.dumps(template["diagnostics"], sort_keys=True)) + 2
    eval_size = len(json.dumps(template["eval"])) + 20
    total = 0
    for c in cells:
        n = c.ct.updates(unit)
        total += len(json.dumps(template["train"])) + len(c.ct.readout_updates(unit)) * eval_size
        if c.learned:
            total += n * update_line + (n // DIAG_EVERY_REAL) * diag_line
    return total


def write_registry(template: dict[str, Any], run_dir: Path, unit: int, diag_every: int) -> dict[str, Any]:
    """The whole registry for candidate A5-D, with missing cells, one failed cell, one non-finite value and a replaced draw (draw 3 by the first reserve)."""
    cells = [*core.q1_cells(False), *core.wx_cells(CANDIDATE), *core.probe_cells(CANDIDATE)]
    learned = [c for c in cells if c.learned and c.block == "Q1"]
    missing = {c.label for c in learned[-MISSING_LABELS:]}
    failed = learned[0].label
    nan = learned[1].label
    written = 0
    for c in cells:
        if c.label in missing:
            continue
        written += write_cell(template, c, run_dir, unit, diag_every, failed=c.label == failed, nan=c.label == nan)
    names = core.draw_names("registered")
    seed_set_of = {str(k): n for k, n in enumerate(names, start=1)}
    seed_set_of["3"] = core.RESERVE_NAMES[0]
    core.write_record(run_dir / "draw_plan.json", {**core.envelope("draw_plan"), "ok": True, "seed_set_of": seed_set_of, "replacements": {"3": core.RESERVE_NAMES[0]}, "labels": {"3": core.replacement_label(core.RESERVE_NAMES[0])}, "reason": ""})
    core.write_record(run_dir / "gates.json", {**core.envelope("gates"), **syn.passing_gates()})
    core.write_record(run_dir / "q1_start.json", {**core.envelope("q1_gate"), "cut3": False, "label": "no cut"})
    core.write_record(run_dir / "q1_gate.json", {**core.envelope("q1_gate"), "cut3": False, "candidate": CANDIDATE, "test_candidate": False, "outcome_row": 4, "outcome": "synthetic", "blocks": {"wx": {"run": True, "status": None}, "probe": {"run": True, "status": None}}})
    return {"cells_written": len(cells) - len(missing), "missing": sorted(missing), "failed": failed, "non_finite": nan, "bytes": written}


def run_worker(run_dir: Path, worker: str, tiny: bool, arm_selection: Path, repo: Path) -> float:
    mode = ["--dry"] if tiny else ["--mode", "check"]
    cmd = [sys.executable, "-m", "studies.p10s0.stages", "work", worker, *mode, "--run-dir", str(run_dir)]
    if worker == "analyze":
        cmd += ["--arm-selection", str(arm_selection)]
    started = time.monotonic()
    proc = subprocess.run(cmd, cwd=repo, capture_output=True, text=True, check=False, env={**os.environ, "PYTHONPATH": str(repo)})  # noqa: S603
    seconds = time.monotonic() - started
    if proc.returncode != 0:
        raise MeasureError(f"work {worker} exited {proc.returncode}: {proc.stderr[-800:]}")
    return seconds


ROW_PATTERNS: dict[str, Callable[[], analysis.RunData]] = {
    "all cells succeed, no candidate": lambda: syn.make_run(),
    "A0 unreliable, candidate A5-D, WX and probe": lambda: syn.make_run(patterns=syn.a0_unreliable(), candidate="A5-D"),
    "every learned cell fails, candidate A1": lambda: syn.make_run(default="bad", candidate="A1"),
    "missing cells": lambda: syn.make_run(patterns=syn.a0_unreliable(), candidate="A5-D", missing={c.label for c in core.q1_cells(False)[:12]}),
    "non-finite cells": lambda: syn.make_run(patterns=syn.a0_unreliable(), candidate="A5-D", nan_cells={c.label for c in core.q1_cells(False)[:12]}),
    "a gate failed": lambda: syn.make_run(patterns=syn.a0_unreliable(), candidate="A5-D", gates={**syn.passing_gates(), "g4_passed": False}),
    "cut 3": lambda: syn.make_run(patterns=syn.a0_unreliable(), candidate="A1", cut3=True),
    "row 1: the arm-selection mapping says not started": lambda: syn.make_run(selection=syn.selection_record(arm_selection.P9IIFacts(False, arm_selection.ADDRESSING_RELIABLE, "COMPLETE", "A0"))),
    "row 3: A6 below its floor on ten draws": lambda: syn.make_run(patterns=syn.a0_unreliable(), a6_bad={"2K/4K": set(range(1, 11)), "8K/16K": set(range(1, 11))}),
    "row 5: qualified at 4,096 only": lambda: syn.make_run(patterns={**syn.a0_unreliable(), ("A5-D", "8K/16K"): syn.failing_draws(set(range(1, 11))), ("A1", "8K/16K"): syn.failing_draws(set(range(1, 11)))}),
    "row 6: nothing qualifies": lambda: syn.make_run(default="bad"),
    "WX and probe not run": lambda: syn.make_run(patterns=syn.a0_unreliable(), candidate="A5-D", block_status={"wx": "NOT RUN — BUDGET", "probe": "NOT RUN — MEMORY"}),
}


def time_rows(work: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for name, build in ROW_PATTERNS.items():
        run = build()
        t0 = time.monotonic()
        result = analysis.analyze(run)
        analysis_seconds = time.monotonic() - t0
        run_dir = work / "rows" / f"r{len(out)}"
        run_dir.mkdir(parents=True)
        core.write_record(run_dir / "analysis.json", core.jsonable({**core.envelope("analysis"), "dry": False, "profile": "registered", "result": result}))
        t1 = time.monotonic()
        report.write_report(run_dir, run_dir / "results")
        out.append({"pattern": name, "outcome_row": result["outcome"]["row"], "analysis_seconds": analysis_seconds, "report_seconds": time.monotonic() - t1})
    return out


def measure(out: Path, *, root: Path | None, tiny: bool, keep: bool, repo: Path | None = None, arm_selection: Path | None = None) -> dict[str, Any]:
    if out.exists():
        raise MeasureError(f"{out} exists")
    repo = repo or core.repo_root()
    arm_selection = arm_selection or repo / "studies/p10s0/freeze/arm_selection.json"
    work = Path(tempfile.mkdtemp(prefix="p10s0-measure-", dir=root))
    try:
        unit = TINY_UNIT if tiny else core.UPDATES
        diag_every = DIAG_EVERY_TINY if tiny else DIAG_EVERY_REAL
        template = make_template(work, TINY_UNIT)
        print(json.dumps({"expected_bytes": expected_bytes(template, unit), "work_dir": str(work), "tiny": tiny}), flush=True)
        run_dir = work / "registry"
        run_dir.mkdir()
        t0 = time.monotonic()
        registry = write_registry(template, run_dir, unit, diag_every)
        build_seconds = time.monotonic() - t0
        analysis_seconds = run_worker(run_dir, "analyze", tiny, arm_selection, repo)
        report_seconds = run_worker(run_dir, "report", tiny, arm_selection, repo)
        rows = time_rows(work)
        row_analysis, row_report = max(r["analysis_seconds"] for r in rows), max(r["report_seconds"] for r in rows)
        record = {
            **core.envelope("timing"), "label": "MEASURED wall seconds on synthetic records and test seeds (no registered input); a statement about this machine and these records only", "tiny": tiny, "unit_updates": unit,
            "registry": {**{k: v for k, v in registry.items() if k != "bytes"}, "bytes_written": registry["bytes"]}, "build_seconds": build_seconds, "analysis_stage_seconds": analysis_seconds, "report_stage_seconds": report_seconds,
            "rows": rows, "outcome_rows_reached": sorted({r["outcome_row"] for r in rows}), "max_row_analysis_seconds": row_analysis, "max_row_report_seconds": row_report,
            "analysis_wall_seconds": analysis_seconds + row_analysis, "report_wall_seconds": report_seconds + row_report,
            "for_caps": not tiny, "rule": "analysis_wall_seconds = the worker's wall time on the full file registry plus the largest in-process analysis over the rows (computation counted twice: errs high); report likewise",
            "environment": core.environment(),
        }  # fmt: skip
        core.write_record(out, core.jsonable(record))
        return record
    finally:
        if not keep:
            shutil.rmtree(work, ignore_errors=True)
