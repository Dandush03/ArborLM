# ruff: noqa: E501
"""The cost-recording stage (ADR-0025 section 8.5; ADR-0022 section 10.2): the five cost measures written from a run.

1. teacher inference per accepted item (Part Q's charged generation seconds over its accepted counts); 2. student training (seconds, updates, rows per update, peak resident memory of each cell type);
3. footprint (parameter counts of the student, the store, the adapters and the teachers; the stored-size arithmetic); 4. active work as COUNTS (reads per item, key products per read, value rows read per
item, adapter parameters applied per generated token: ``evaluate.active_work``) and the counted training multiply-adds per update (``cost.training_multiply_adds``); 5. the timing benchmark (descriptive).

EVERY figure is printed with ``cost.COST_NOTE``: it enters no label, it is a count of logical work or a recorded duration, never measured efficiency and never a speedup. TRAINING COST COMPARABLE is not printed
(ADR-0025 section 3 row 20): the training seconds are recorded without a comparison label.
"""

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import torch

from arborlm.io import read_json
from studies.p10s2.classes import stored_size_line
from studies.p10s2.evaluate import active_work
from studies.p10s2.model import student_parameter_count
from studies.p10s2.train import reads_of

from . import cost, engine
from .common import core

NOTE = cost.COST_NOTE


def teacher_inference(qdir: Path | None) -> dict[str, Any]:
    """Seconds of teacher generation per accepted training item, from Part Q's charged ledger and its generation counts (None, 'not recorded' if either is absent)."""
    if qdir is None or not (qdir / "charged_ledger.json").is_file() or not (qdir / "generation/result.json").is_file():
        return {"seconds_per_accepted_item": None, "note": "not recorded"}
    led = read_json(qdir / "charged_ledger.json")
    gen_seconds = sum(float(e["seconds"]) for e in led["entries"] if e["stage"] == "generation")
    counts = read_json(qdir / "generation/result.json")["counts"]
    n = sum(counts.values())
    return {"generation_seconds_charged": gen_seconds, "accepted_items": n, "seconds_per_accepted_item": gen_seconds / n if n else None, "type": "recorded duration"}


def training_records(run_dir: Path) -> dict[str, Any]:
    """Seconds, updates, rows per update, trainable parameters and peak resident memory by arm, medians over the cells of an arm, from the cell records and the stage manifest."""
    cells = [read_json(p) for p in sorted((run_dir / "tasks" / "train").glob("*.cell.json"))]
    man = read_json(run_dir / "train" / "manifest.json") if (run_dir / "train" / "manifest.json").is_file() else {"tasks": {}}
    by: dict[str, list[dict[str, Any]]] = {}
    for c in cells:
        arm = c["label"].split("/")[1]
        by.setdefault(arm, []).append(c)
    out: dict[str, Any] = {}
    for arm, rs in by.items():
        sec = sorted(float(r["wall_seconds"]) for r in rs)
        peaks = sorted(float(t.get("peak_rss_bytes", 0)) for k, t in man["tasks"].items() if f"|{arm}|" in k)
        out[arm] = {
            "cells": len(rs), "median_wall_seconds": sec[len(sec) // 2], "updates": rs[0]["updates"], "trainable_parameters": rs[0]["trainable_parameters"], "device": rs[0]["device"],
            "median_peak_rss_bytes": peaks[len(peaks) // 2] if peaks else None,
        }  # fmt: skip
    return out


def footprint(world: engine.WorldT, teachers: Sequence[int] = (73_944_309, 74_669_178)) -> dict[str, Any]:
    """Parameter counts: the student, the store (N and 2N rows), the LoRA adapters (rank 42 and 84), E-table; and the stored-size arithmetic of ADR-0022 section 11.5 as P10-S2's ``stored_size_line`` prints it
    (without the G values: they are the analysis's)."""
    from studies.p10s2.model import lora_parameter_count, store_parameter_count

    cfg = world.cfg
    s = student_parameter_count(cfg)
    return {
        "student_parameters": s, "store_parameters_N": store_parameter_count(cfg, world.rows_per_stage), "store_parameters_2N": store_parameter_count(cfg, 2 * world.rows_per_stage), "lora_rank_single": lora_parameter_count(cfg, world.rank_single),
        "lora_rank_joint": lora_parameter_count(cfg, world.rank_joint), "etable_parameters_per_capability": (world.vocabulary + 1) * cfg.width + 1,
        "stored_size_line": stored_size_line(s, 2 * world.rows_per_stage, list(teachers), None, None, cfg.width), "type": "analytical count",
    }  # fmt: skip


def active_work_counts(world: engine.WorldT, snap_dir: Path, rep: int = 0) -> dict[str, Any]:
    """Logical counts per generated token for the arms the lines read (``evaluate.active_work``): reads per item from the stored E_A prompts, generated tokens per item from the replicate's training rows."""
    ctx = world.ctx
    reads = [len(reads_of(ex, ["A"], world.marker_index)) for ex in ctx.panels["E_A"].examples]
    rows = world.train_examples(rep, "A")
    gen_tokens = sum(max(1, len(e.ids) - e.prompt_len) for e in rows) / max(1, len(rows))
    out = {}
    for arm in ("M1", "M-append", "D1", "D-append"):
        a = engine.load_t(world, rep, snap_dir, f"r{rep}/{arm}/AB")
        out[arm] = active_work(a, sum(reads) / len(reads), gen_tokens)
    return {**out, "reads_per_item": sum(reads) / len(reads), "generated_tokens_per_item": gen_tokens}


def counted_updates(world: engine.WorldT) -> dict[str, Any]:
    """Counted training multiply-adds per update for each arm kind at batch 32 and the mean training sequence length of replicate 0 (``cost.training_multiply_adds``; every reading is in that module's docstring).
    D-append counts its frozen first adapter's forward and input-gradient work once and the trainable second adapter's twice, as the module's reading (4) says."""
    shape = cost.StudentShape(cfg_width(world), world.cfg.layers, world.cfg.heads, world.cfg.kv_heads, world.cfg.intermediate, world.cfg.vocab)
    rows = world.train_examples(0, "A")
    mean_len = sum(len(e.ids) for e in rows) / len(rows)
    mean_reads = sum(len(e.reads) + 1 for e in rows) / len(rows)
    n = world.rows_per_stage
    kw = {"batch": world.batch, "mean_len": mean_len, "mean_reads": mean_reads, "read_block": world.layer}
    out = {
        "M1": cost.training_multiply_adds(shape, "memory", rows=n, trainable_rows=n, **kw), "M-append": cost.training_multiply_adds(shape, "memory", rows=2 * n, trainable_rows=n, **kw),
        "M-seq": cost.training_multiply_adds(shape, "memory", rows=n, trainable_rows=n, **kw), "M-ii": cost.training_multiply_adds(shape, "memory", rows=2 * n, trainable_rows=2 * n, **{**kw, "batch": world.batch + world.replay_rows}),
        "D1": cost.training_multiply_adds(shape, "lora", lora_rank=world.rank_single, **{k: v for k, v in kw.items() if k not in ("mean_reads", "read_block")}),
        "D-seq": cost.training_multiply_adds(shape, "lora", lora_rank=world.rank_single, **{k: v for k, v in kw.items() if k not in ("mean_reads", "read_block")}),
        "D-append": cost.training_multiply_adds(shape, "lora", lora_rank=world.rank_single, frozen_lora_rank=world.rank_single, **{k: v for k, v in kw.items() if k not in ("mean_reads", "read_block")}),
    }  # fmt: skip
    return {"per_update": out, "batch": world.batch, "mean_training_sequence_length": mean_len, "mean_reads_per_row": mean_reads, "note": NOTE}


def cfg_width(world: engine.WorldT) -> int:
    return int(world.cfg.width)


def timing_record(run_dir: Path) -> dict[str, Any]:
    p = run_dir / "timing" / "stage_record.json"
    return read_json(p) if p.is_file() else {"status": "not yet measured"}


def lines(rec: Mapping[str, Any]) -> list[str]:
    """The printed lines, each under the note; the fixed oracle-assisted line is put above by the caller."""
    out = []
    ti = rec["teacher_inference"]
    out.append(f"teacher inference per accepted item: {ti.get('seconds_per_accepted_item')} s ({NOTE})")
    for arm, r in sorted(rec["student_training"].items()):
        out.append(f"student training, {arm}: median {r['median_wall_seconds']:.1f} s for {r['updates']} updates, {r['trainable_parameters']} trainable parameters, peak resident {r['median_peak_rss_bytes']} bytes on {r['device']} (recorded, no comparison label; {NOTE})")
    fp = rec["footprint"]
    out.append(f"footprint: student {fp['student_parameters']}, store N {fp['store_parameters_N']}, store 2N {fp['store_parameters_2N']}, LoRA r42 {fp['lora_rank_single']}, r84 {fp['lora_rank_joint']} ({NOTE}); {fp['stored_size_line']}")
    for arm, w in sorted(rec["active_work"].items()):
        if isinstance(w, dict):
            out.append(f"active work, {arm}: {w} ({NOTE})")
    for arm, c in sorted(rec["counted_training"]["per_update"].items()):
        out.append(f"counted training multiply-adds per update, {arm}: forward {c['forward']:.4g}, backward {c['backward']:.4g}, total {c['total']:.4g} ({NOTE})")
    tm = rec["timing"]
    out.append(f"timing benchmark: {tm.get('status')} (descriptive; {NOTE})")
    return out


def record(world: engine.WorldT, run_dir: Path, qdir: Path | None, snap_dir: Path) -> dict[str, Any]:
    rec = {
        "teacher_inference": teacher_inference(qdir), "student_training": training_records(run_dir), "footprint": footprint(world), "active_work": active_work_counts(world, snap_dir), "counted_training": counted_updates(world),
        "timing": timing_record(run_dir), "note": NOTE,
    }  # fmt: skip
    return rec


def write(run_dir: Path, rec: Mapping[str, Any]) -> None:
    core.write_record(run_dir / "cost.json", {**core.envelope("report", "T"), "kind_of_content": "cost", **core.jsonable(dict(rec))}, overwrite=True)
    (run_dir / "cost.txt").write_text(core.under_line(*lines(rec)) + "\n", encoding="utf-8")


def mean_tensor(x: Sequence[torch.Tensor]) -> float:
    return float(torch.stack(list(x)).mean())
