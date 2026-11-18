# ruff: noqa: E501
"""P10IR stage A2 adapter (ADR-0029 section 10): trains the bridge cells through P10-S1's own model and training functions, without editing them and without touching their seed whitelist.

Why new code: ``studies/p10s1/train.py`` ``run_job`` calls ``check_job_seeds`` (``core.check_seed_set``), which accepts only P10-S1's own seed-set names (``p10s1-draw-1..5`` in registered mode). The bridge
draws (bases 290001 + 100 (d - 1)) are not P10-S1's. The legitimate route, as the ADR states: ``run_cell`` below is ``train.run_job`` without ``check_job_seeds`` (and without its ``updates.jsonl`` and
P10-S1 train record), calling ``train.job_model``, ``train.Trainer.step``, ``train.snapshot_marks`` and ``train.save_snapshot`` unedited. Nothing is patched, wrapped or replaced inside P10-S1; this
study's seed gate (``gates.seed_gate``, section 11 item 6) replaces the whitelist for the bridge values (registry section 4.3 item 4).

The adapter identity gate (R3-2): given one P10-S1 registered cell's draw and initialisation seed (F-OQ and T-OQ at 8K/4K, draw 1, initialisation 2101), the adapter reproduces that cell's stored checkpoint
at its first three snapshots (512, 1,024, 2,048): every tensor of the state dict equal (``torch.equal``) to the stored ``model.pt``'s, and the snapshot written through ``train.save_snapshot`` under
P10-S1's cell label has an identical ``model_sha256``. Bit-exact: on the platform of record only.
"""

import os
import shutil
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import torch

from arborlm.io import file_sha256, read_json
from studies.p10s1 import core as s1core
from studies.p10s1 import train

from . import core, gates, items

TRAIN_LR = s1core.LEARNING_RATE


def bridge_cell(arm: str, facts: int, slots: int, draw: int, u_p: int, run: int, cfg: Mapping[str, Any] | None = None) -> s1core.Cell:
    """The bridge cell as a P10-S1 ``Cell`` (``make_cell`` is P10-S1's; its label format carries the bridge initialisation seed): P10-S1's rate and lengths, a bridge draw and initialisation seed."""
    c = cfg or core.load_config()
    if abs(float(c["a2"]["learning_rate"]) - TRAIN_LR) > 0:
        raise ValueError("A2 is pinned to P10-S1's learning rate")
    return s1core.make_cell("P", arm, facts, slots, draw, core.bridge_init_seed(draw, c), u_p=u_p, run_updates=run, lr=TRAIN_LR)


def job_for(cell: s1core.Cell, data: Any, seeds: Any, backbone: Any, out_dir: Path, snapshots: Sequence[int], *, max_updates: int | None = None, mode: str = "p10ir") -> train.TrainJob:
    """The training job of a cell, as ``studies.p10s1.stages.build_job`` builds it (stream over the cell's facts, hash seed base + 40, the optimizer kept at the run length only)."""
    return train.TrainJob(
        cell=cell, data=data, stream=train.training_stream_for(data, cell.facts), backbone=backbone, out_dir=out_dir, r1_seed=seeds.r1_codes, hash_seed=s1core.h8_seed(seeds), mode=mode,
        updates=cell.run_updates, snapshots=tuple(snapshots), optimizer_marks=(cell.run_updates,), max_updates=max_updates,
    )  # fmt: skip


def run_cell(job: train.TrainJob, *, keep_optimizer: bool = True) -> dict[str, Any]:
    """``train.run_job`` without ``check_job_seeds``: build the model (``train.job_model``, which seeds Python's and torch's generators with the initialisation seed as P9 does), the trainer, run the updates
    (``Trainer.step``) and write the snapshots through ``train.save_snapshot``. Returns the snapshot hashes and the cost."""
    began = time.monotonic()
    model = train.job_model(job)
    trainer = train.Trainer(job, model)
    start = trainer.update
    last = job.updates if job.max_updates is None else min(job.updates, job.max_updates)
    marks = train.snapshot_marks(job, start, last)
    keep_opt = (set(job.optimizer_marks) if job.optimizer_marks is not None else {last}) if keep_optimizer else set()
    job.out_dir.mkdir(parents=True, exist_ok=True)
    hashes: dict[str, str] = {}
    for update in range(start + 1, last + 1):
        trainer.step(job.stream.batch(update))
        if update in marks:
            hashes[str(update)] = train.save_snapshot(job.out_dir, update, model, trainer.optimizers, trainer.snapshot_extra(), keep_optimizer=update in keep_opt, write_json=True)["model_sha256"]
    return {"snapshot_sha256": hashes, "updates": trainer.update, "seconds": time.monotonic() - began, "peak_rss_bytes": train.peak_rss(), "movement": trainer.movement()}


def assert_seed_allowed(mode: str, spec: Mapping[str, Any], cfg: Mapping[str, Any] | None = None) -> None:
    """The seed check at the point of training (audit A4; it replaces P10-S1's whitelist for the bridge values). Registered mode: the draw's seed set and initialisation seed are exactly
    ``core.bridge_seeds(draw)`` and ``core.bridge_init_seed(draw)``, and every value of the set lies in the registry's bridge range. Rehearsal and test modes: the set lies in the test range or the
    rehearsal range, never in P10-S1's registered draws or the bridge range."""
    c = cfg or core.load_config()
    base, draw, init = int(spec["seed_base"]), int(spec["draw"]), int(spec["init_seed"])
    values = core.seed_set_values(s1core.seed_set(str(spec["seed_name"]), base))
    rng = c["seed_ranges"]
    if mode == "registered":
        want = core.bridge_seeds(draw, c)
        lo, hi = (int(x) for x in rng["bridge"])
        if spec["seed_name"] != want.name or base != want.facts or init != core.bridge_init_seed(draw, c) or not all(lo <= v <= hi for v in values):
            raise ValueError(f"refused: {spec['seed_name']} base {base} init {init} are not the registered bridge seeds of draw {draw}")
        return
    ok = [tuple(int(x) for x in rng[k]) for k in ("test", "rehearsal")]
    if not all(any(lo <= v <= hi for lo, hi in ok) for v in values) or init not in {int(x) for x in c["seeds"]["test_init"]} | {int(c["seeds"]["rehearsal_init"])}:
        raise ValueError(f"refused: {spec['seed_name']} base {base} init {init} are not test or rehearsal seeds")


# --- a bridge cell -------------------------------------------------------------------------------------------------------------------------------------
def train_bridge_cell(ctx: items.Ctx, cell_label: str, plan_cells: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """Train one planned bridge cell into ``<run>/A2/train/cells/<label>`` (built in ``<label>.partial`` and renamed when complete; a stale partial from a killed run is removed first, which re-runs the
    same cell with the same settings). A cell that has a ``train.failed.json`` is kept and not re-run (section 11)."""
    spec = plan_cells[cell_label]
    root = ctx.run_dir / "A2" / "train" / "cells"
    final, partial = root / cell_label, root / f"{cell_label}.partial"
    if (final / "train.json").is_file():
        return read_json(final / "train.json")  # type: ignore[no-any-return]
    if (root / f"{cell_label}.failed.json").is_file():
        raise RuntimeError(f"{cell_label} failed before and is kept, not re-run (section 11)")
    if partial.exists():
        shutil.rmtree(partial)
    assert_seed_allowed(ctx.mode, spec)
    probe = {"seed_name": spec["seed_name"], "seed_base": spec["seed_base"], "table_facts": spec["table_facts"], "unseen": spec["unseen"], "stage": core.STAGE_A2}
    data, seeds = items.load_data(ctx, probe)
    cell = s1core.make_cell("P", spec["arm"], spec["facts"], spec["slots"], spec["draw"], spec["init_seed"], u_p=spec["u_p"], run_updates=spec["run"], lr=TRAIN_LR)
    if cell.label != cell_label:
        raise ValueError(f"the planned cell label {cell_label} is not the label of its cell {cell.label}")
    job = job_for(cell, data, seeds, items.backbone_of(ctx), partial, spec["snapshots"])
    try:
        result = run_cell(job)
    except Exception as exc:
        root.mkdir(parents=True, exist_ok=True)
        core.write_record(root / f"{cell_label}.failed.json", {**core.envelope("bridge_train"), "label": cell_label, "status": "failed", "reason": type(exc).__name__ + ": " + str(exc)})
        raise
    record = {
        **core.envelope("bridge_train"), "label": cell_label, "status": "completed", "arm": cell.arm, "facts": cell.facts, "slots": cell.slots, "draw": cell.draw, "init_seed": cell.init_seed, "u_p": cell.u_p,
        "run_updates": cell.run_updates, "learning_rate": cell.lr, "seed_name": spec["seed_name"], "snapshots": list(spec["snapshots"]), "platform": gates.platform_record(), **result,
    }  # fmt: skip
    core.write_record(partial / "train.json", record)
    os.replace(partial, final)
    return record


# --- the adapter identity gate ---------------------------------------------------------------------------------------------------------------------------------
def identity_gate(ctx: items.Ctx, work_dir: Path, *, cells: Sequence[tuple[str, int, int, int, int, int, int]], seeds_of: Any, updates: Sequence[int], cfg: Mapping[str, Any] | None = None, record: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Train each listed P10-S1 cell (``(arm, facts, slots, draw, init_seed, u_p, run)``) through the adapter for ``max(updates)`` updates under P10-S1's cell label and compare, at each of ``updates``, with
    the stored checkpoint: ``torch.equal`` on every tensor of the state dict and an identical ``model_sha256`` of the snapshot file. A mismatch stops stage A2 before training. Platform of record only."""
    c = cfg or core.load_config()

    def run() -> tuple[bool, dict[str, Any]]:
        detail: dict[str, Any] = {"cells": {}}
        ok = True
        for arm, facts, slots, draw, init_seed, u_p, run_len in cells:
            cell = s1core.make_cell("P", arm, facts, slots, draw, init_seed, u_p=u_p, run_updates=run_len)
            seeds = seeds_of(draw)
            probe = {"seed_name": seeds.name, "seed_base": seeds.facts, "table_facts": ctx.sizes["table_facts"], "unseen": ctx.sizes["unseen"], "stage": core.STAGE_A1}
            data, _ = items.load_data(ctx, probe, verify=False)
            out = work_dir / cell.label
            if out.exists():
                shutil.rmtree(out)
            job = job_for(cell, data, seeds, items.backbone_of(ctx), out, list(updates), max_updates=max(updates), mode="p10ir-identity")
            run_cell(job, keep_optimizer=False)
            per: dict[str, Any] = {}
            for u in updates:
                stored_dir = ctx.s1_run_dir / "cells" / cell.label / "snapshots" / s1core.snapshot_stem(u)  # type: ignore[operator]
                new_dir = out / "snapshots" / s1core.snapshot_stem(u)
                stored = torch.load(stored_dir / "model.pt", weights_only=True, map_location="cpu")["model"]
                new = torch.load(new_dir / "model.pt", weights_only=True, map_location="cpu")["model"]
                tensors = stored.keys() == new.keys() and all(torch.equal(stored[k], new[k]) for k in stored)
                recorded = read_json(stored_dir / "snapshot.json")["model_sha256"]
                same_hash = file_sha256(new_dir / "model.pt") == recorded
                per[str(u)] = {"tensors_equal": bool(tensors), "model_sha256_equal": bool(same_hash)}
                ok = ok and tensors and same_hash
            detail["cells"][cell.label] = per
        detail["updates"] = list(updates)
        detail["rate"] = float(c["a2"]["learning_rate"])
        return ok, detail

    problems = gates.platform_problems(c, record)
    if problems:
        return gates.gate("tree", None, reason="not the platform of record: " + "; ".join(problems), name="adapter_identity")
    ok, detail = run()
    return gates.gate("tree", ok, name="adapter_identity", **detail)
