# ruff: noqa: E501
"""Calibration and the pilot gate (ADR-0022 sections 12.1, 12.2). The rule and the runner; nothing here is run against registered or real data in this implementation step.

Calibration (before the freeze; calibration seeds; D_cal only). Store: L in {4, 12} at learning rate 0.003, for each capability: 4 cells. LoRA: learning rate in {0.0003, 0.001}, for each capability: 4 cells.
Each is a Stage 1 of U = 2,000 updates on calibration draws, with a snapshot at 1,000 updates. Rule: the setting with the higher mean over the two capabilities of chrF on D_cal; a difference below 0.01 goes
to the first value listed. If the rehearsal rule selects U = 1,000, the selection rule and the pilot gate are applied to the 1,000-update snapshots. Calibration scores are never reported as results.
Nothing else is tuned. Evaluation panels are not scored before the registered run.

Pilot gate: with the calibrated store setting, on D_cal, Stage 1 for both capabilities (the calibration cells; no extra training). If either has a gap closed below 0.25 the registered run does not start:
NOT STARTED: STUDENT CANNOT USE THE MEMORY ON THIS TASK, recorded with the calibration records. The pilot's scores are optimistic (D_cal also selected the setting); they are not results.
"""

import copy
import dataclasses
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import torch

from . import core, evaluate
from .memory import MemoryArm, NullArm, SparseStore, new_lora_arm
from .text import chrf_item, gap_closed, mean
from .train import train_arm
from .world import World

PILOT_STOP = "NOT STARTED: STUDENT CANNOT USE THE MEMORY ON THIS TASK"
CAL = core.CFG["calibration"]


@dataclass(frozen=True)
class CalCell:
    kind: str  # "store" | "lora"
    setting: float  # the read layer L (store) or the learning rate (LoRA)
    capability: str

    @property
    def label(self) -> str:
        return f"cal/{self.kind}/{self.setting:g}/{self.capability}"


class CalibrationFailed(RuntimeError):
    """A calibration cell did not complete (a device error, a non-finite loss or a stage stop): the calibration is not interpretable and nothing is selected."""


def cpu_snapshot(arm: Any) -> Any:
    """A copy of the arm taken mid-training, on CPU. The arm is on the training device (MPS in the registered path) when the snapshot is taken, and scoring runs on CPU: a copy left on the training device
    raised ``RuntimeError: mat1 is on CPU, expected GPU`` at the first 1,000-update snapshot (audit B1)."""
    snap = copy.deepcopy(arm)
    snap.to(torch.device("cpu"))
    return snap


def calibration_cells() -> list[CalCell]:
    """The 8 cells (4 store, 4 LoRA)."""
    return [*(CalCell("store", float(ly), c) for ly in CAL["read_layers"] for c in core.TASKS), *(CalCell("lora", float(lr), c) for lr in CAL["lora_lrs"] for c in core.TASKS)]


@dataclass(frozen=True)
class Selection:
    read_layer: int
    lora_lr: float
    store_scores: Mapping[str, float]
    lora_scores: Mapping[str, float]


def _pick(values: list[float], score: Mapping[float, float], tol: float) -> float:
    """The setting with the higher mean over the capabilities; a difference below ``tol`` goes to the first value listed."""
    best = values[0]
    for v in values[1:]:
        if score[v] - score[best] >= tol:
            best = v
    return best


def select(scores: Mapping[str, float]) -> Selection:
    """``scores`` maps a calibration cell label to its chrF on D_cal. The rule of section 12.1. A non-finite or missing score raises (the calibration is not interpretable)."""
    tol = core.CFG["training"]["calibration_selection_min_difference"]
    for c in calibration_cells():
        v = scores.get(c.label)
        if v is None or v != v:
            raise ValueError(f"calibration score missing or not finite: {c.label}")
    layers = [float(x) for x in CAL["read_layers"]]
    lrs = [float(x) for x in CAL["lora_lrs"]]
    store_mean = {ly: sum(scores[CalCell("store", ly, c).label] for c in core.TASKS) / 2 for ly in layers}
    lora_mean = {lr: sum(scores[CalCell("lora", lr, c).label] for c in core.TASKS) / 2 for lr in lrs}
    return Selection(int(_pick(layers, store_mean, tol)), _pick(lrs, lora_mean, tol), {str(k): v for k, v in store_mean.items()}, {str(k): v for k, v in lora_mean.items()})


def pilot_gate(g_by_capability: Mapping[str, float | None]) -> dict[str, Any]:
    """If either capability's gap closed on D_cal is below 0.25 (or undefined), the registered run does not start."""
    thr = core.CFG["gates"]["pilot_gap_min"]
    failed = [c for c in core.TASKS if g_by_capability.get(c) is None or g_by_capability[c] < thr]
    return {"ok": not failed, "outcome": None if not failed else PILOT_STOP, "failed_capabilities": failed, "g": dict(g_by_capability), "note": "optimistic: D_cal also selected the setting; not a result"}


def run_calibration(world: World, replicate: int, *, updates: int, snapshot_updates: int | None = None) -> dict[str, Any]:
    """Train and score the 8 calibration cells (Stage 1 each) on the world's calibration draw ``replicate`` and D_cal. ``world`` must be built in calibration mode with calibration seeds (the seed
    function refuses anything else). Returns the scores at ``updates`` and at the snapshot, the selection (at ``updates`` and at the snapshot) and the pilot gate."""
    snap_at = snapshot_updates if snapshot_updates is not None else int(CAL["updates"] // 2)
    plan = world.plan(replicate)
    ctx = world.ctx
    ctx.seed_plan = plan
    s0 = {c: evaluate.score_panel(ctx, NullArm(), world.d_cal[c], route="none").mean for c in core.TASKS}
    teacher = {c: mean([chrf_item(o, rf) for o, rf in zip(world.teacher_outputs[c]["D_cal"], world.d_cal[c].refs, strict=True)]) for c in core.TASKS}
    final: dict[str, float] = {}
    snap: dict[str, float] = {}
    for cell in calibration_cells():
        w = dataclasses.replace(world, layer=int(cell.setting)) if cell.kind == "store" else world
        codes = w.codes(replicate)
        if cell.kind == "store":
            arm: Any = MemoryArm(SparseStore.new(w.cfg.width, w.rows_per_stage, plan.gen(0, "stage-1 store (calibration)")), w.layer, codes)
            lr = float(CAL["store_lr"])
        else:
            arm = new_lora_arm(w.cfg, w.rank_single, plan.gen(8, "LoRA initialization (calibration)"))
            lr = cell.setting
        holder: dict[str, Any] = {}

        def on_update(u: int, arm: Any = arm, holder: dict[str, Any] = holder) -> None:
            if u == snap_at:
                holder["snap"] = cpu_snapshot(arm)

        trec = train_arm(w.student, arm, w.train_examples(replicate, cell.capability), updates, w.batch, lr, plan.gen(2, "batch order (calibration)"), w.marker_index, device=w.device, on_update=on_update)
        if trec.status != "completed":
            raise CalibrationFailed(f"{cell.label}: {trec.error}")
        panel = w.d_cal[cell.capability]
        final[cell.label] = evaluate.score_panel(ctx, arm, panel).mean
        snap[cell.label] = evaluate.score_panel(ctx, holder["snap"], panel).mean if "snap" in holder else float("nan")
    sel = select(final)
    pilot_scores = {c: final[CalCell("store", float(sel.read_layer), c).label] for c in core.TASKS}
    g = {c: gap_closed(pilot_scores[c], s0[c], teacher[c]) for c in core.TASKS}
    out: dict[str, Any] = {"scores": final, "snapshot_scores": snap, "selection": dataclasses.asdict(sel), "pilot": pilot_gate(g), "stage0_d_cal": s0, "teacher_d_cal": teacher, "device": str(world.device), "updates": updates, "snapshot_updates": snap_at, "note": "calibration scores are never reported as results"}
    if all(v == v for v in snap.values()):
        sel_s = select(snap)
        out["selection_at_snapshot"] = dataclasses.asdict(sel_s)
        g_s = {c: gap_closed(snap[CalCell("store", float(sel_s.read_layer), c).label], s0[c], teacher[c]) for c in core.TASKS}
        out["pilot_at_snapshot"] = pilot_gate(g_s)
    return out
