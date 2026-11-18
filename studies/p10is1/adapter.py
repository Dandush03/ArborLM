# ruff: noqa: E501
"""P10IS1 adapter (ADR-0024 sections 6, 7.2 item 6, 14): trains this study's cells through P10-S1's own model and training functions, without editing them and without touching their seed whitelist.

Why new code: ``studies/p10s1/train.py`` ``run_job`` calls ``check_job_seeds`` (``core.check_seed_set``), which accepts only P10-S1's own seed-set names. This study's data seeds (240001-240499, calibration 249001 and
249101, rehearsal 249201, tests 933001-933999) are not P10-S1's. ``run_segment`` is ``train.run_job``'s loop without that call: it calls ``train.job_model``, ``train.Trainer`` (``step``, ``resume``) and
``train.save_snapshot`` unedited. Nothing is patched, wrapped or replaced inside P10-S1; ``assert_seed_allowed`` replaces the whitelist at the point of use (and this study's seed gate checks the values against the registry).

Continuation (gate G4, restoration): a cell is trained in segments (to U0, then ladder point by ladder point). A segment resumes from the largest complete snapshot that kept its optimizer state (``Trainer.resume``);
a resumed run equals an uninterrupted one bit for bit on the platform of record (the identity gate and ``tests/test_p10is1_adapter.py``). A non-finite loss, gradient norm or parameter stops the cell at that update, recorded
FAILED — NON-FINITE with the update index; it is kept and never re-run (ADR-0024 section 14). The adapter identity gate reproduces P10-S1's stored F-OQ and T-OQ checkpoints (``torch.equal`` on every tensor).
"""

import shutil
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import torch

from arborlm.io import file_sha256, read_json
from studies.p10s1 import core as s1core
from studies.p10s1 import train

from . import core, gates

TRAIN_RECORD = "cell_train.json"
FAILED_RECORD = "cell_failed.json"


class NonFinite(RuntimeError):
    """A non-finite loss, gradient norm or parameter at ``update`` (ADR-0024 section 14): FAILED — NON-FINITE, kept, not re-run, never a verdict."""

    def __init__(self, update: int, detail: str) -> None:
        super().__init__(f"FAILED — NON-FINITE at update {update}: {detail}")
        self.update = update


def cell_dir(run_dir: Path, label: str, group: str = "train") -> Path:
    return run_dir / group / "cells" / label


def cell_of(spec: Mapping[str, Any], mode: str | None = None) -> s1core.Cell:
    """P10-S1's ``Cell`` of a planned cell; its label must be the plan's."""
    cell = core.make_cell(mode or str(spec.get("mode", core.REGISTERED)), spec["arm"], spec["facts"], spec["slots"], spec["draw"], spec["init_seed"], u_p=spec["u_p"], run=spec["run"], lr=spec["lr"], kind=spec.get("kind", "P"))
    if cell.label != spec["label"]:
        raise ValueError(f"the planned cell label {spec['label']} is not the label of its cell {cell.label}")
    return cell


# --- seeds at the point of use ------------------------------------------------------------------------------------------------------------------
def assert_seed_allowed(mode: str, spec: Mapping[str, Any], cfg: Mapping[str, Any] | None = None) -> None:
    """Replaces P10-S1's whitelist (audit A4). Registered: the draw's seed set and initialisation seed are exactly ``core.registered_seeds(draw)`` and ``core.init_seed_of(draw)``, every value inside the registry's
    block M range. Calibration: the set and initialisation are one of the two calibration pairs. Rehearsal: the rehearsal draw and its initialisation. Test: a set of the test range and a test initialisation. Anything else is
    refused (and a registered mode never accepts a calibration, rehearsal or test seed)."""
    c = core.cfg_of(cfg)
    rng = c["seed_ranges"]
    base, init, name = int(spec["seed_base"]), int(spec["init_seed"]), str(spec["seed_name"])
    values = core.seed_set_values(s1core.seed_set(name, base))

    def inside(key: str) -> bool:
        lo, hi = (int(x) for x in rng[key])
        return all(lo <= v <= hi for v in values)

    if mode == core.REGISTERED:
        draw = int(spec["draw"])
        want = core.registered_seeds(draw, c)
        if name != want.name or base != want.facts or init != core.init_seed_of(draw, c) or not inside("registered"):
            raise ValueError(f"refused: {name} base {base} init {init} are not the registered block M seeds of draw {draw}")
        return
    if mode == "calibration":
        k = int(spec["draw"])
        want = core.calibration_seeds(k, c)
        if name != want.name or base != want.facts or init != core.calibration_init(k, c) or not inside("calibration"):
            raise ValueError(f"refused: {name} base {base} init {init} are not the calibration seeds of draw {k}")
        return
    if mode == core.REHEARSAL:
        want = core.rehearsal_seeds(c)
        if name != want.name or base != want.facts or init != int(c["seeds"]["rehearsal_init"]) or not inside("rehearsal"):
            raise ValueError(f"refused: {name} base {base} init {init} are not the rehearsal seeds")
        return
    if mode == core.TEST:
        if not inside("test") or init not in {int(x) for x in c["seeds"]["test_init"]}:
            raise ValueError(f"refused: {name} base {base} init {init} are not test seeds")
        return
    raise ValueError(f"unknown mode {mode!r}")


# --- jobs ---------------------------------------------------------------------------------------------------------------------------------------
def job_for(cell: s1core.Cell, data: Any, seeds: Any, backbone: Any, out_dir: Path, snapshots: Sequence[int], *, optimizer_marks: Sequence[int], max_updates: int | None = None, init_snapshot: Path | None = None, mode: str = "calibration") -> train.TrainJob:
    """The training job of a cell, as ``studies.p10s1.stages.build_job`` builds it (stream over the cell's facts, hash seed base + 40, the optimizer kept at the marks given)."""
    return train.TrainJob(
        cell=cell, data=data, stream=train.training_stream_for(data, cell.facts), backbone=backbone, out_dir=out_dir, r1_seed=seeds.r1_codes, hash_seed=s1core.h8_seed(seeds), mode=mode, updates=cell.run_updates,
        snapshots=tuple(snapshots), optimizer_marks=tuple(optimizer_marks), init_snapshot=init_snapshot, max_updates=max_updates, fact_lut=train.fact_lut_for(data, cell.facts) if cell.arm == "R2" else None,
    )  # fmt: skip


def resumable_snapshots(out_dir: Path) -> list[int]:
    """Updates at which a snapshot is complete (``snapshot.json`` written last) and kept its optimizer state: the points a segment can resume from."""
    root = out_dir / "snapshots"
    if not root.is_dir():
        return []
    out = []
    for d in sorted(root.iterdir()):
        if (d / "snapshot.json").is_file() and (d / "optimizer.pt").is_file() and (d / "model.pt").is_file():
            out.append(int(d.name[1:]))
    return out


def completed_snapshots(out_dir: Path) -> list[int]:
    root = out_dir / "snapshots"
    return sorted(int(d.name[1:]) for d in root.iterdir() if (d / "snapshot.json").is_file() and (d / "model.pt").is_file()) if root.is_dir() else []


def run_segment(job: train.TrainJob, *, keep_end_optimizer: bool = True) -> dict[str, Any]:
    """``train.run_job``'s loop without ``check_job_seeds``: build the model (``train.job_model``, which seeds Python's and torch's generators with the initialisation seed as P9 does), the trainer, resume from
    ``job.init_snapshot`` if given, run the updates (``Trainer.step``) up to ``job.max_updates`` (or the run length) and write the snapshots through ``train.save_snapshot``. Returns the snapshot hashes, the process CPU
    seconds at each snapshot (descriptive) and the cost. A non-finite value raises ``NonFinite`` with the update index."""
    began, cpu0 = time.monotonic(), time.process_time()
    model = train.job_model(job)
    trainer = train.Trainer(job, model)
    if job.init_snapshot is not None:
        trainer.resume(job.init_snapshot)
    start = trainer.update
    last = job.updates if job.max_updates is None else min(job.updates, job.max_updates)
    marks = train.snapshot_marks(job, start, last)
    keep_opt = set(job.optimizer_marks or ()) | ({last} if keep_end_optimizer else set())
    job.out_dir.mkdir(parents=True, exist_ok=True)
    hashes: dict[str, str] = {}
    cpu: dict[str, float] = {}
    for update in range(start + 1, last + 1):
        try:
            trainer.step(job.stream.batch(update))
        except ValueError as exc:
            if str(exc).startswith("non-finite"):
                raise NonFinite(update, str(exc)) from exc
            raise
        if update in marks or update == last:
            hashes[str(update)] = train.save_snapshot(job.out_dir, update, model, trainer.optimizers, trainer.snapshot_extra(), keep_optimizer=update in keep_opt, write_json=True)["model_sha256"]
            cpu[str(update)] = time.process_time() - cpu0
    return {"snapshot_sha256": hashes, "start": start, "end": trainer.update, "cpu_seconds_at_snapshot": cpu, "seconds": time.monotonic() - began, "peak_rss_bytes": train.peak_rss(), "movement": trainer.movement()}


def train_to(data: Any, seeds: Any, backbone: Any, run_dir: Path, spec: Mapping[str, Any], to_update: int, *, mode: str, group: str = "train", cfg: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Train one planned cell up to ``to_update`` (a segment: from the largest resumable snapshot below it, or from scratch), writing the planned snapshots at or below it and keeping the optimizer at ``to_update``.
    The cumulative record ``cell_train.json`` is rewritten after each segment. A cell with ``cell_failed.json`` is kept and not re-run (section 14). A segment that is already complete is not recomputed."""
    out = cell_dir(run_dir, spec["label"], group)
    if (out / FAILED_RECORD).is_file():
        raise RuntimeError(f"{spec['label']} failed before and is kept, not re-run (section 14)")
    assert_seed_allowed(mode, spec, cfg)
    cell = cell_of(spec, mode if mode != "calibration" else core.REHEARSAL)
    have = completed_snapshots(out)
    if to_update in have:
        return read_json(out / TRAIN_RECORD) if (out / TRAIN_RECORD).is_file() else {"trained_to": to_update}
    resumable = [u for u in resumable_snapshots(out) if u <= to_update]
    start = max(resumable) if resumable else 0
    marks = [u for u in spec["snapshots"] if start < u <= to_update]
    init = None if start == 0 else out / "snapshots" / s1core.snapshot_stem(start)
    root = out / "snapshots"
    for d in sorted(root.iterdir()) if root.is_dir() else []:  # snapshots written after the last resumable point by a killed run (complete or half-written) are rewritten identically (G4): remove them
        if int(d.name[1:]) > start:
            shutil.rmtree(d)
    job = job_for(cell, data, seeds, backbone, out, marks, optimizer_marks=(to_update,), max_updates=to_update, init_snapshot=init, mode="calibration")
    try:
        seg = run_segment(job)
    except NonFinite as exc:
        core.write_record(out / FAILED_RECORD, {**core.envelope("train"), "label": spec["label"], "status": "failed", "reason": str(exc), "failed_update": exc.update, "platform": gates.platform_record()}, overwrite=True)
        raise
    prior = read_json(out / TRAIN_RECORD) if (out / TRAIN_RECORD).is_file() else {"segments": [], "snapshot_sha256": {}}
    rec = {
        **core.envelope("train"), "label": spec["label"], "status": "completed", "arm": spec["arm"], "facts": spec["facts"], "slots": spec["slots"], "draw": spec["draw"], "init_seed": spec["init_seed"], "u_p": spec["u_p"],
        "learning_rate": spec["lr"], "run_planned": spec["run"], "trained_to": seg["end"], "seed_name": spec["seed_name"], "platform": gates.platform_record(),
        "snapshot_sha256": {**prior["snapshot_sha256"], **seg["snapshot_sha256"]}, "segments": [*prior["segments"], {"from": seg["start"], "to": seg["end"], "seconds": seg["seconds"], "cpu_seconds_at_snapshot": seg["cpu_seconds_at_snapshot"], "peak_rss_bytes": seg["peak_rss_bytes"]}],
        "movement": seg["movement"],
    }  # fmt: skip
    core.write_record(out / TRAIN_RECORD, rec, overwrite=True)
    return rec


# --- the adapter identity gate ---------------------------------------------------------------------------------------------------------------------
def identity_gate(s1_run_dir: Path, work_dir: Path, *, data: Any, seeds: Any, backbone: Any, cells: Sequence[tuple[str, int, int, int, int, int, int]], updates: Sequence[int], cfg: Mapping[str, Any] | None = None, record: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Train each listed P10-S1 cell (``(arm, facts, slots, draw, init_seed, u_p, run)``) through the adapter for ``max(updates)`` updates under P10-S1's cell label and compare with the stored checkpoint at each of
    ``updates``: ``torch.equal`` on every tensor of the state dict and an identical ``model_sha256`` of the snapshot file written through ``train.save_snapshot``. Platform of record only; elsewhere skipped. Also
    resumes a segment from the middle and compares the final tensors with the uninterrupted run (restoration, G4)."""
    problems = gates.platform_problems(cfg, record)
    if problems:
        return gates.gate("adapter identity gate", None, name="adapter_identity", reason="not the platform of record: " + "; ".join(problems))
    detail: dict[str, Any] = {"cells": {}}
    ok = True
    for arm, facts, slots, draw, init_seed, u_p, run_len in cells:
        cell = s1core.make_cell("P", arm, facts, slots, draw, init_seed, u_p=u_p, run_updates=run_len)
        out = work_dir / cell.label
        if out.exists():
            shutil.rmtree(out)
        job = job_for(cell, data, seeds, backbone, out, list(updates), optimizer_marks=(), max_updates=max(updates), mode="calibration")
        run_segment(job, keep_end_optimizer=False)
        per: dict[str, Any] = {}
        for u in updates:
            stored_dir = s1_run_dir / "cells" / cell.label / "snapshots" / s1core.snapshot_stem(u)
            new_dir = out / "snapshots" / s1core.snapshot_stem(u)
            stored = torch.load(stored_dir / "model.pt", weights_only=True, map_location="cpu")["model"]
            new = torch.load(new_dir / "model.pt", weights_only=True, map_location="cpu")["model"]
            tensors = stored.keys() == new.keys() and all(torch.equal(stored[k], new[k]) for k in stored)
            same_hash = file_sha256(new_dir / "model.pt") == read_json(stored_dir / "snapshot.json")["model_sha256"]
            per[str(u)] = {"tensors_equal": bool(tensors), "model_sha256_equal": bool(same_hash)}
            ok = ok and tensors and same_hash
        detail["cells"][cell.label] = per
    detail["updates"] = list(updates)
    return gates.gate("adapter identity gate", ok, name="adapter_identity", **detail)


def restoration_check(data: Any, seeds: Any, backbone: Any, work_dir: Path, spec: Mapping[str, Any], split: int, end: int, *, mode: str, cfg: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """G4: a run stopped at ``split`` and resumed to ``end`` equals an uninterrupted run to ``end``, tensor for tensor (``torch.equal``) and by the file hash of the last snapshot."""
    cell = cell_of(spec, mode)
    marks = [split, end]
    a, b = work_dir / "uninterrupted", work_dir / "resumed"
    for d in (a, b):
        if d.exists():
            shutil.rmtree(d)
    run_segment(job_for(cell, data, seeds, backbone, a, marks, optimizer_marks=(end,), max_updates=end, mode="calibration"))
    run_segment(job_for(cell, data, seeds, backbone, b, [split], optimizer_marks=(split,), max_updates=split, mode="calibration"))
    run_segment(job_for(cell, data, seeds, backbone, b, [end], optimizer_marks=(end,), max_updates=end, init_snapshot=b / "snapshots" / s1core.snapshot_stem(split), mode="calibration"))
    ta = torch.load(a / "snapshots" / s1core.snapshot_stem(end) / "model.pt", weights_only=True, map_location="cpu")["model"]
    tb = torch.load(b / "snapshots" / s1core.snapshot_stem(end) / "model.pt", weights_only=True, map_location="cpu")["model"]
    equal = ta.keys() == tb.keys() and all(torch.equal(ta[k], tb[k]) for k in ta)
    return {"tensors_equal": bool(equal), "model_sha256_equal": file_sha256(a / "snapshots" / s1core.snapshot_stem(end) / "model.pt") == file_sha256(b / "snapshots" / s1core.snapshot_stem(end) / "model.pt"), "split": split, "end": end, "platform": gates.platform_record()}


def remove_tree(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)

