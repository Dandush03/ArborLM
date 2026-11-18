# ruff: noqa: E501
"""Part T's stages over a world: train every cell in dependency order, score every snapshot, build the registry (ADR-0025 sections 5, 8, 10).

``train_all`` and ``score_all`` are what the registered stages call per task (a task is one cell or one replicate's scoring); the tests call them on a tiny world. Every record is plain data. Training uses the
frozen device (MPS in a registered run, CPU in tests), scoring CPU. A cell that stops on a non-finite loss is not resumed and stops the cells that depend on it (their status is ``skipped_dependency``).
"""

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import torch

from studies.p10s2 import combined as combined_mod
from studies.p10s2.cells import AdapterRouteArm, CompositeStoreArm
from studies.p10s2.memory import MemoryArm

from . import engine, scoring
from .common import core
from .quantities import NONE, ORDERS, REPLICATES, Registry

ORDER_ARMS = ("M1", "D1", "M-append", "M-seq", "M-ii", "D-append", "D-seq")
JOINT = ("M-joint", "D-joint")


def cell_specs(replicates: tuple[int, ...] = REPLICATES) -> list[engine.CellSpec]:
    """Every trained cell in dependency order: per (replicate, order) the stage-1 modules then the stage-2 modules; per replicate the joint arms and E-table."""
    out: list[engine.CellSpec] = []
    for r in replicates:
        for o in ORDERS:
            out += [engine.CellSpec(a, o, r) for a in ORDER_ARMS]
        out += [engine.CellSpec(a, NONE, r) for a in JOINT]
        out += [engine.CellSpec("E-table", NONE, r, c) for c in core.TASKS]
    return out


def train_all(world: engine.WorldT, snap_dir: Path, ckpt_dir: Path | None, updates: int, replicates: tuple[int, ...] = REPLICATES) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for spec in cell_specs(replicates):
        parent = spec.parent
        if parent is not None and records.get(parent.label, {}).get("status") != "COMPLETE":
            records[spec.label] = {"label": spec.label, "status": "skipped_dependency", "depends_on": parent.label}
            continue
        rec, _ = engine.run_cell(world, spec, updates, snap_dir, ckpt_dir)
        records[spec.label] = rec
    return records


@torch.no_grad()
def score_all(world: engine.WorldT, snap_dir: Path, gloss_bank: Mapping[str, Any], replicates: tuple[int, ...] = REPLICATES) -> tuple[Registry, dict[str, Any]]:
    """Score every snapshot (CPU) into the registry's reads; returns the registry and the side records (router diagnostics, modification)."""
    records: dict[str, dict[str, float]] = scoring.reference_records(world)
    side: dict[str, Any] = {}
    for r in replicates:
        routers = scoring.build_routers_t(world, r)
        side[f"r{r}/routers"] = {"/".join(k): v[1] for k, v in routers.items()}
        for o in ORDERS:
            arms = {a: engine.load_t(world, r, snap_dir, f"r{r}/{a}/{o}") for a in ORDER_ARMS}
            for a in ORDER_ARMS:
                reads, extra = scoring.cell_reads(world, r, a, o, arms[a], routers, m1=arms["M1"])
                records[f"{a}|{o}|{r}"] = reads
                if extra:
                    side[f"r{r}/{a}/{o}"] = extra
        for a in JOINT:
            arm = engine.load_t(world, r, snap_dir, f"r{r}/{a}/-")
            reads = scoring.panel_means(world, arm)
            if isinstance(arm, MemoryArm):
                reads |= scoring.control_reads(world, r, arm, a, "AB")
            records[f"{a}|-|{r}"] = reads
        table = {c: engine.load_t(world, r, snap_dir, f"r{r}/E-table/{c}") for c in core.TASKS}
        records[f"E-table|-|{r}"] = {f"s:{scoring.PANEL[c]}": scoring.panel_means(world, table[c])[f"s:{scoring.PANEL[c]}"] for c in core.TASKS}
        m1 = {"A": engine.load_t(world, r, snap_dir, f"r{r}/M1/AB"), "B": engine.load_t(world, r, snap_dir, f"r{r}/M1/BA")}
        d1 = {"A": engine.load_t(world, r, snap_dir, f"r{r}/D1/AB"), "B": engine.load_t(world, r, snap_dir, f"r{r}/D1/BA")}
        records[f"M-sep|-|{r}"] = scoring.panel_means(world, CompositeStoreArm(m1))  # type: ignore[arg-type]
        records[f"D-sep|-|{r}"] = scoring.panel_means(world, AdapterRouteArm(d1))  # type: ignore[arg-type]
        for name, v in scoring.baseline_reads(world, r, gloss_bank).items():
            arm, read = name.split("|", 1)
            if read.startswith("hits"):
                side.setdefault(f"r{r}/R-exact-hits", {})[read] = v
            else:
                records.setdefault(f"{arm}|-|{r}", {})[read] = v
    return scoring.registry_from_reads(records), side


@torch.no_grad()
def combined_all(world: engine.WorldT, snap_dir: Path, replicates: tuple[int, ...] = REPLICATES) -> dict[str, Any]:
    """C1 and C2 on the twelve arm-cells per replicate (stage-2 snapshots of M-append, M-ii, D-seq and D-append in both orders, M-joint, D-joint, M-sep, D-sep), plus S0 and the ensemble: oracle route, never trained on."""
    from studies.p10s2.memory import NullArm

    ctx, out = world.ctx, {}
    out["S0"] = combined_mod.score_combined_cell(ctx, NullArm(), ctx.ec)
    out["ensemble"] = combined_mod.ensemble_record(ctx.ec, {c: world.teacher_outputs[c]["E_C"] for c in core.TASKS})
    for r in replicates:
        ctx.seed_plan = world.plan(r)  # type: ignore[assignment]
        for o in ORDERS:
            for a in ("M-append", "M-ii", "D-seq", "D-append"):
                out[f"{a}|{o}|{r}"] = combined_mod.score_combined_cell(ctx, engine.load_t(world, r, snap_dir, f"r{r}/{a}/{o}"), ctx.ec)
        for a in JOINT:
            out[f"{a}|-|{r}"] = combined_mod.score_combined_cell(ctx, engine.load_t(world, r, snap_dir, f"r{r}/{a}/-"), ctx.ec)
        m1 = {"A": engine.load_t(world, r, snap_dir, f"r{r}/M1/AB"), "B": engine.load_t(world, r, snap_dir, f"r{r}/M1/BA")}
        d1 = {"A": engine.load_t(world, r, snap_dir, f"r{r}/D1/AB"), "B": engine.load_t(world, r, snap_dir, f"r{r}/D1/BA")}
        out[f"M-sep|-|{r}"] = combined_mod.score_combined_cell(ctx, CompositeStoreArm(m1), ctx.ec)  # type: ignore[arg-type]
        out[f"D-sep|-|{r}"] = combined_mod.score_combined_cell(ctx, AdapterRouteArm(d1), ctx.ec)  # type: ignore[arg-type]
    return out
