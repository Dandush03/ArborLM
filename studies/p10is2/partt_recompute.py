# ruff: noqa: E501
"""Part T's independent recomputation path (ADR-0025 section 8.6; ADR-0022 section 13.3, rulings B-M9 and C-M3).

No result is reported before every registered score is recomputed on CPU from the STORED snapshots of the cells (the cell outputs; no cell is trained again). With the frozen scoring code every score must be
BIT-IDENTICAL (tolerance 0); with the auditor's own code every greedy sequence must be identical and every item score within 1e-6 (``own_code``: means within 1e-6 here; the sequences are the auditor's
to compare, from the snapshots). A difference beyond the tolerance is ENGINEERING STOP — RECOMPUTATION: both values and the cell are recorded and NOTHING is labelled (``partt_real.require_recomputation``
makes the analysis refuse). It re-scores in a fresh process on CPU at six threads with deterministic algorithms; its time is charged (ruling L2).
"""

import math
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import torch

from . import engine, partt_items, partt_run, scoring
from .common import core, gates
from .quantities import Thresholds

OWN_CODE_TOLERANCE = 1e-6
FROZEN_CODE_TOLERANCE = 0.0


def compare(registered: Mapping[str, float], recomputed: Mapping[str, float], tolerance: float) -> list[dict[str, Any]]:
    """Every registered key against its recomputed value; a key missing on either side, a non-finite value or a difference above ``tolerance`` is a difference."""
    diffs: list[dict[str, Any]] = []
    for k in sorted(set(registered) | set(recomputed)):
        a, b = registered.get(k), recomputed.get(k)
        if a is None or b is None:
            diffs.append({"key": k, "registered": a, "recomputed": b, "difference": None, "why": "missing on one side"})
        elif not (math.isfinite(a) and math.isfinite(b)):
            diffs.append({"key": k, "registered": a, "recomputed": b, "difference": None, "why": "non-finite"})
        elif abs(a - b) > tolerance:
            diffs.append({"key": k, "registered": a, "recomputed": b, "difference": abs(a - b)})
    return diffs


def combined_means(comb: Mapping[str, Any]) -> dict[str, float]:
    """The numbers of the combined records that enter a description: each kind's mean, tested means and single-task means."""
    out: dict[str, float] = {}
    for name, rec in comb.items():
        for kind in ("C1", "C2"):
            if kind in rec:
                out[f"{name}|{kind}|mean"] = float(rec[kind]["mean"])
                for lang in core.TASKS:
                    v = rec[kind]["tested_by_language"].get(lang)
                    if v is not None:
                        out[f"{name}|{kind}|tested|{lang}"] = float(v)
        if "single" in rec:
            for lang in core.TASKS:
                s = rec["single"]["scores"][lang]
                out[f"{name}|single|{lang}"] = sum(map(float, s)) / max(1, len(s))
    return out


def recompute(world: engine.WorldT, run_dir: Path, gloss: Mapping[str, Any], registered: Mapping[str, float], combined_registered: Mapping[str, Any] | None = None, *, own_code: bool = False, replicates: tuple[int, ...] = (0, 1, 2), routers_mode: str = "load", stored_items: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Re-score every snapshot of the run on CPU and compare with the registry (and the combined records' means). Returns the record written as ``recomputation.json``."""
    tol = OWN_CODE_TOLERANCE if own_code else FROZEN_CODE_TOLERANCE
    keep, world.device = world.device, torch.device("cpu")
    try:
        scoring.ITEMS.clear()
        records = partt_run.reference_task(world)
        for r in replicates:
            rec, _ = partt_run.score_replicate(world, r, run_dir / "snapshots", gloss, routers_mode=routers_mode)  # "load": the routers the evaluation snapshotted, hash-checked, never new ones
            records.update(rec)
        again = scoring.registry_from_reads(records).values
        diffs = compare(registered, again, tol)
        item_diffs = partt_items.compare_items(stored_items, scoring.take_items(), tol) if stored_items is not None else []
        cdiffs: list[dict[str, Any]] = []
        if combined_registered is not None:
            comb = partt_run.combined_reference(world)
            for r in replicates:
                comb.update(partt_run.combined_replicate(world, r, run_dir / "snapshots", pinned_orders=partt_run.rejected_orders(registered, r, Thresholds.from_config(world.cfg_t).modification_dcon_tolerance)))
            cdiffs = compare(combined_means(combined_registered), combined_means(comb), tol)
    finally:
        world.device = keep
    return {
        "ok": not diffs and not cdiffs and not item_diffs, "outcome": None if not (diffs or cdiffs or item_diffs) else "ENGINEERING STOP — RECOMPUTATION", "checked": len(registered), "tolerance": tol, "code": "own" if own_code else "frozen", "differences": diffs + cdiffs + item_diffs,
        "item_records_compared": None if stored_items is None else len(stored_items), "routers_mode": routers_mode,
        "platform": gates.platform_record(), "note": "a difference is an engineering stop: both values and the cell are recorded and nothing is labelled",
    }  # fmt: skip


def attempts(run_dir: Path) -> list[Path]:
    d = run_dir / "recomputation"
    return sorted(d.glob("attempt_*.json")) if d.is_dir() else []


def write(run_dir: Path, rec: Mapping[str, Any]) -> Path:
    """Writes ``recomputation/attempt_<n>.json``: every attempt is KEPT (a failed one is never erased by running the recomputation again; ruling 13). The record of an attempt says which snapshots, routers and per-item
    files it read."""
    d = run_dir / "recomputation"
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"attempt_{len(attempts(run_dir)) + 1:03d}.json"
    core.write_record(path, {**core.envelope("recomputation", "T"), **core.jsonable(dict(rec))}, overwrite=False)
    return path
