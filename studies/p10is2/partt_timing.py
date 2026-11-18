# ruff: noqa: E501
"""The timing benchmark's stage body (ADR-0025 section 10, stage 7; ADR-0022 section 10.2). DESCRIPTIVE: no wall-time comparison and no label is registered on it.

One process, six threads, CPU, the timed arms S0, M-append, D-append, D-seq, E-table and R-icl on the stored timing items (200 per panel, seed 250913: ``bundle.extra["timing_items"]``), three repetitions, median.
It runs ALONE: the attempt is opened only if no process of this or any other study is alive, the quiet condition (1-minute load average at most 2.0 after at least 60 seconds with no study process) is read BEFORE
each repetition (``timing.run_attempt``), every wait is bounded, and an attempt that cannot start a repetition within 30 minutes of its opening ends INCOMPLETE ATTEMPT with its completed repetitions kept. The first
attempt with three completed repetitions is the record. NOT MEASURED is a recorded DECISION of the lead after five attempts without one: this module writes it only when that decision file exists. Its duration
is charged to the ledger (it is not a plan stage and has no stage cap of its own: the part's total cap applies).
"""

import os
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

import psutil
import torch

from arborlm.io import read_json, write_json
from studies.p10s2 import retrieval
from studies.p10s2.cells import icl_ids
from studies.p10s2.evaluate import score_panel
from studies.p10s2.memory import NullArm

from . import engine, partt_tasks, timing
from .common import core
from .common.core import StageRefused

DECISION_FILE = "NOT_MEASURED_DECISION.md"


def own_study_alive() -> list[str]:
    """Command lines of live processes of THIS study other than this one (a worker or a stage of Part Q or T)."""
    me = os.getpid()
    out = []
    for p in psutil.process_iter(["pid", "cmdline"]):
        try:
            text = " ".join(p.info["cmdline"] or [])
        except psutil.Error:
            continue
        if p.info["pid"] != me and "python" in text and "studies.p10is2" in text:
            out.append(text[:200])
    return out


def anything_alive() -> list[str]:
    return [*partt_tasks.other_studies_alive(), *own_study_alive()]


def make_repetition(world: engine.WorldT, snap_dir: Path, items: int | None = None, clock: Callable[[], float] = time.perf_counter, rep: int = 0) -> Callable[[], float]:
    """One repetition: every timed arm scores the stored timing items of E_A and E_B under the oracle route on CPU, one process, one item at a time; returns the total seconds and keeps the per-arm seconds in
    ``repetition.detail``."""
    ctx = world.ctx
    timing_items = {k: list(v) for k, v in getattr(world, "timing_items", {}).items()}

    def pick(panel: str) -> list[int]:
        idx = timing_items.get(panel) or list(range(len(ctx.panels[panel].examples)))
        return idx[:items] if items else idx

    arms = {
        "S0": NullArm(), "M-append": engine.load_t(world, rep, snap_dir, f"r{rep}/M-append/AB"), "D-append": engine.load_t(world, rep, snap_dir, f"r{rep}/D-append/AB"), "D-seq": engine.load_t(world, rep, snap_dir, f"r{rep}/D-seq/AB"),
        "E-table": engine.load_t(world, rep, snap_dir, f"r{rep}/E-table/A"),
    }  # fmt: skip
    detail: list[dict[str, float]] = []

    @torch.no_grad()
    def one() -> float:
        per: dict[str, float] = {}
        t_all = clock()
        keep, world.device = world.device, torch.device("cpu")
        try:
            for name, arm in arms.items():
                t0 = clock()
                for panel in ("E_A", "E_B"):
                    if name == "E-table" and panel == "E_B":
                        continue  # the table of capability A is read on E_A only
                    score_panel(ctx, arm, ctx.panels[panel], indices=pick(panel))
                per[name] = clock() - t0
            t0 = clock()
            for c in core.TASKS:
                train = world.streams[rep].t[c]
                idx = retrieval.TfidfIndex(train)
                panel = "E_A" if c == "A" else "E_B"
                for i in pick(panel):
                    it = world.partition.panels[panel][i]
                    demos = retrieval.r_icl_prompt_items(train, it.en, 4, idx)
                    ids = icl_ids([world.bank.train(c, d) for d in demos], ctx.panels[panel].examples[i])
                    ctx.student.greedy(torch.tensor([ids]), add=None, adapter=None, max_new=ctx.max_new, stop_bytes=ctx.decoder.table)
            per["R-icl"] = clock() - t0
        finally:
            world.device = keep
        detail.append(per)
        return clock() - t_all

    one.detail = detail  # type: ignore[attr-defined]
    return one


def attempts_of(directory: Path) -> list[dict[str, Any]]:
    return [read_json(p) for p in sorted(directory.glob("attempt_*.json"))]


def run_stage(cfg: Mapping[str, Any], directory: Path, repetition: Callable[[], float], *, clock: Callable[[], float] = time.monotonic, sleep: Callable[[float], None] = time.sleep, load_fn: Callable[[], float] | None = None, alive_fn: Callable[[], Sequence[str]] = anything_alive) -> dict[str, Any]:
    """One invocation of the benchmark stage: refuses unless nothing is alive at the opening; runs ONE attempt; writes ``attempt_<n>.json``; returns the stage record. After five attempts without three
    completed repetitions the stage waits for the lead's recorded decision (``NOT_MEASURED_DECISION.md`` in the directory) and only then records NOT MEASURED."""
    directory.mkdir(parents=True, exist_ok=True)
    past = attempts_of(directory)
    rec = timing.stage_record(past, cfg)
    if rec["status"] == "MEASURED":
        return rec
    if rec["status"] == "NEEDS DECISION: NOT MEASURED":
        if (directory / DECISION_FILE).is_file():
            out = {**rec, "status": "NOT MEASURED", "decision": (directory / DECISION_FILE).read_text()[:500], "note": "NOT MEASURED by the lead's recorded decision after five attempts; the stage is closed"}
            write_json(directory / "stage_record.json", core.jsonable(out))
            return out
        raise StageRefused("refused: five attempts did not give three completed repetitions; NOT MEASURED needs the lead's recorded decision (NOT_MEASURED_DECISION.md in the timing directory)")
    alive = list(alive_fn())
    if alive:
        raise StageRefused(f"refused: the timing benchmark runs alone; processes alive: {alive[:3]}")
    attempt = timing.run_attempt(repetition, cfg=cfg, clock=clock, sleep=sleep, load_fn=load_fn or (lambda: os.getloadavg()[0]), alive_fn=alive_fn)
    attempt["detail_per_arm_seconds"] = list(getattr(repetition, "detail", []))
    attempt["attempt"] = len(past) + 1
    attempt["threads"] = torch.get_num_threads()
    write_json(directory / f"attempt_{len(past) + 1}.json", core.jsonable(attempt))
    out = timing.stage_record([*past, attempt], cfg)
    write_json(directory / "stage_record.json", core.jsonable({k: v for k, v in out.items() if k != "record"} | {"statuses": [a["status"] for a in [*past, attempt]]}))
    return out
