# ruff: noqa: E501
"""Part Q's two rehearsals (ADR-0025 section 10, "Part Q rehearsals, sealed"; section 11 item 5).

A MEASURING rehearsal runs steps 1 to 8 with one generation block per capability and one Q_check block under the fixed cap (3.0 charged hours); it cannot be frozen on. It measures seconds per unit,
peak memory, disk use and the load, and its records feed the caps by code. A COUNTING rehearsal runs the candidate plan file itself (its SHA-256 goes into the record) limited to two generation blocks per
capability and one Q_check block, with ONE forced pause and resume and ONE forced PAUSED — IDENTITY and restore, and may reuse the measuring rehearsal's completed blocks (same seeds and layout, so
identical). The values of Q1-Q4 and every per-item score go to a sealed file; the record prints only the whitelist (ruling L5): timings, memory, counts, yields, the chosen filter setting.

The drivers take injected pieces (a context factory over the real or the synthetic world, an identity probe) so the same code runs the real rehearsals and the tests.
"""

import os
import resource
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from ..common import core, gates
from . import batches as bt
from . import pipeline

CONTEXT_KEYS_SEALED = ("q1", "q2", "q3", "q4", "grid", "per_item", "mean_chrf", "student", "values", "precision", "chrf")


def load_average() -> tuple[float, float, float]:
    return os.getloadavg()


def peak_rss_mib() -> float:
    """Peak resident set of this process (macOS reports bytes, Linux kilobytes)."""
    r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return float(r) / (1024 * 1024) if os.uname().sysname == "Darwin" else float(r) / 1024


def disk_bytes(path: Path) -> int:
    return int(sum(f.stat().st_size for f in path.rglob("*") if f.is_file())) if path.exists() else 0


def stage_statuses(ctx: pipeline.QContext) -> dict[str, bool]:
    """Which registered stages have a complete record on disk: nothing is called COMPLETE that did not run (``inputs`` and ``outputs`` are written by the real path's step 1 and step 8)."""
    have = lambda name: ctx.d(name).is_file()  # noqa: E731
    return {
        "inputs": have("inputs/record.json"), "partition": have("partition_counts.json"), "qfit": have("qfit/record.json"), "qcheck": have("qcheck/teacher_A/result.json") and have("qcheck/teacher_B/result.json"),
        "generation": have("generation/result.json"), "regeneration": have("regeneration.json"), "outputs": have("outputs/record.json"),
    }  # fmt: skip


def whitelist(summary: Mapping[str, Any]) -> dict[str, Any]:
    """Ruling L5: the sealed run may show timings, memory, counts, yields, the chosen filter setting and batches. Anything else is dropped; a key that names a quality value is refused outright."""
    bad = [k for k in summary if any(s in k.lower() for s in CONTEXT_KEYS_SEALED)]
    if bad:
        raise ValueError(f"refused: sealed key(s) in a displayed summary: {bad}")
    allowed = ("timings", "memory", "counts", "yields", "filter_setting", "batches", "sources", "disk_bytes", "load", "workers", "platform")
    return {k: v for k, v in summary.items() if k in allowed}


def rates_and_units(ctx: pipeline.QContext, external: Mapping[str, tuple[float, float]] | None = None) -> tuple[dict[str, float], dict[str, float]]:
    """Seconds per unit by stage from this run's timings and the units it actually processed, and the units of the FULL run (both split pools generated to the end, the whole Q_check reserve drawn, the whole
    regeneration subsample): Part Q's projection assumes the worst case (section 10 item 3). ``external`` is (seconds, units) for the stages the pipeline does not run itself (inputs, outputs)."""
    have = pipeline._have
    pc = (have(ctx, "partition_counts.json") or {}).get("counts", {})
    qc = {c: have(ctx, f"qcheck/teacher_{c}/result.json") or {} for c in core.TASKS}
    gen = have(ctx, "generation/result.json") or {}
    n_qfit = float(pc.get("panel_sizes", {}).get("Q_fit", 0))
    block = int(ctx.sizes["q_check_block"]) if ctx.sizes and "q_check_block" in ctx.sizes else int(ctx.cfg["panels"]["q_check_block"])
    done = {
        "partition": 1.0, "qfit": 2.0 * n_qfit, "qcheck": float(sum((qc[c].get("stop") or {}).get("blocks_drawn", 0) for c in core.TASKS) * block),
        "generation": float(sum(v.get("sources_generated", 0) for v in (gen.get("per_capability") or {}).values())),
        "regeneration": float(2 * (ctx.regeneration_batches or int(ctx.cfg["generation"]["regeneration_batches"])) * ctx.size),
    }  # fmt: skip
    full = {
        "partition": 1.0, "qfit": 2.0 * n_qfit, "qcheck": float(2 * int(pc.get("reserve_blocks", 0)) * block), "generation": float((gen.get("split") or {}).get("A_sources", 0) + (gen.get("split") or {}).get("B_sources", 0)),
        "regeneration": done["regeneration"],
    }  # fmt: skip
    rates = {k: ctx.timings[k] / done[k] for k in done if done[k] > 0 and k in ctx.timings}
    for k, (sec, units) in (external or {}).items():
        if units > 0:
            rates[k], full[k] = sec / units, units
    return rates, full


def run_measuring(ctx_factory: Callable[[], pipeline.QContext], *, cap_seconds: float, charged_before_freeze_seconds: float = 0.0, external: Mapping[str, tuple[float, float]] | None = None, clock: Callable[[], float] = time.monotonic) -> dict[str, Any]:
    """Steps 1-8 with one generation block per capability and one Q_check block, under ``cap_seconds`` (a fixed cap: 3.0 h). A stop on the cap is PAUSED: the record says so and nothing is hidden."""
    ctx = ctx_factory()
    ctx.max_generation_blocks, ctx.max_check_blocks = 1, 1
    started = clock()
    ctx.deadline = lambda: clock() - started > cap_seconds
    load0 = load_average()
    status = "COMPLETE"
    result: dict[str, Any] | None = None
    try:
        result = pipeline.run_all(ctx)
    except bt.StageCapExceeded:
        status = "PAUSED"
    seconds = clock() - started
    summary = pipeline.summary_for_display(ctx)
    g = (pipeline._have(ctx, "generation/result.json") or {}).get("per_capability") or {}
    units = {c: float(g[c]["sources_generated"]) for c in core.TASKS if c in g}
    rates, full_units = rates_and_units(ctx, external)
    rec = {
        **core.envelope("rehearsal", "Q"), "kind_of_rehearsal": "measuring", "status": status, "rates_seconds_per_unit": rates, "projection_units": full_units, "charged_before_freeze_seconds": charged_before_freeze_seconds, "caps_provisional": True, "cannot_be_frozen_on": True, "fixed_cap_seconds": cap_seconds,
        "timings": {"total_seconds": seconds, "seconds_per_generated_source": {c: seconds / u for c, u in units.items() if u}}, "memory": {"peak_rss_mib": peak_rss_mib()}, "disk_bytes": disk_bytes(ctx.run_dir),
        "load": {"start": load0, "end": load_average(), "note": "the 1-minute load average is the first element"}, "counts": summary["counts"], "yields": summary["yields"], "filter_setting": summary["filter_setting"],
        "platform": gates.platform_record(), "stages": {"all": {"status": status}}, "sealed_values_in": "sealed/ (not read)",
    }  # fmt: skip
    if result is not None:
        rec["label_is_not_reported"] = "the label of a rehearsal is not a result; it is sealed with the values"
    return rec


def run_counting(ctx_factory: Callable[[], pipeline.QContext], *, plan_file_sha256: str, caps_provisional: bool, cap_seconds: float, stage_caps: Mapping[str, float] | None = None, identity_probe: Callable[[], None] | None = None, clock: Callable[[], float] = time.monotonic, pause_after_batches: int = 3) -> dict[str, Any]:
    """The candidate plan file itself, limited to two generation blocks per capability and one Q_check block; ONE forced pause (the cap trips after ``pause_after_batches`` batches) and resume, and ONE forced
    PAUSED — IDENTITY (``identity_probe`` is called once; it must raise ``StageRefused`` for a changed frozen file and succeed after the file is restored) and restore. Each stage it exercises is checked against its
    computed cap (``stage_caps`` in seconds by stage name)."""
    ctx = ctx_factory()
    ctx.max_generation_blocks, ctx.max_check_blocks = 2, 1
    counter = {"n": 0, "armed": True}

    def deadline() -> bool:
        if not counter["armed"]:
            return False
        counter["n"] += 1
        return counter["n"] > pause_after_batches

    ctx.deadline = deadline
    t0 = clock()
    paused = False
    try:
        pipeline.run_all(ctx)
    except bt.StageCapExceeded:
        paused = True
    counter["armed"] = False
    t_pause = clock() - t0
    identity_ok = False
    if identity_probe is not None:
        try:
            identity_probe()  # must refuse
        except core.StageRefused:
            identity_ok = True  # PAUSED — IDENTITY recorded; the probe's restore step is the caller's, and the next line proves the stage resumes
    t1 = clock()
    result = pipeline.run_all(ctx)  # resume: completed blocks are not regenerated
    t_resume = clock() - t1
    summary = pipeline.summary_for_display(ctx)
    done = stage_statuses(ctx)
    stages = {s: {"status": "COMPLETE" if ok else "NOT RUN", "within_cap": None if not stage_caps or s not in stage_caps else (clock() - t0) <= stage_caps[s]} for s, ok in done.items()}
    return {
        **core.envelope("rehearsal", "Q"), "kind_of_rehearsal": "counting", "status": "COMPLETE" if all(v["status"] == "COMPLETE" for v in stages.values()) else "INCOMPLETE", "plan_file_sha256": plan_file_sha256, "caps_provisional": caps_provisional, "fixed_cap_seconds": cap_seconds,
        "stages": stages, "forced": {"pause_resume": paused, "paused_identity_restore": identity_ok}, "timings": {"first_attempt_seconds": t_pause, "resume_seconds": t_resume}, "memory": {"peak_rss_mib": peak_rss_mib()},
        "counts": summary["counts"], "yields": summary["yields"], "filter_setting": summary["filter_setting"], "platform": gates.platform_record(), "load": {"end": load_average()}, "outcome_is_sealed": result["derived"],
    }  # fmt: skip
