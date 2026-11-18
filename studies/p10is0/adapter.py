# ruff: noqa: E501
"""P10IS0 adapter (ADR-0023 section 3): P10-S0's training and evaluation of A5-D, A0 and A6 at slot counts that P9-II's cell registry rejects (512, 1,024, 2,048, 8,192), in new code.

How it calls the underlying functions legitimately (no edit, no patch). ``studies.p9ii.train.Trainer`` and ``studies.p9ii.evaluate.evaluate_readout`` read ``cell.arm``, ``cell.slots``, ``cell.label``, ``cell.stage``, ``cell.draw`` and
``cell.seed_index`` only; the registry check lives in ``studies.p9ii.core.Cell.__post_init__``, which this study's own ``core.Cell`` (a different class with the same attributes) never goes through. The model builder, the losses (including
L_div) and the update step are called from ``studies.p9ii``; the generator, the panels, the read swap and the probe set are P10-S0's and P9's, called as they are.

What differs from ``studies.p10s0.train.run_job``, which keeps every per-update record and diagnostic in memory (``kept``, ``kept_diag``): this loop writes each record to disk when it is produced and keeps none, so its memory does
not grow with run length (section 9; a test bounds it). It writes one file per segment (a segment starts at a snapshot), checkpoints the diagnostics at this study's cadence (every 64 updates up to 4,096, every 1,024 after) and
recognises divergence only by the trainer's own three non-finite checks (ruling 19): every other exception is an item error and an out-of-memory or file-system error is an environment error.

Status: implementation self-checked only.
"""

import os
import re
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import psutil
import torch

from arborlm.io import file_sha256
from studies.p9 import controls
from studies.p9 import core as p9core
from studies.p9 import data as data_mod
from studies.p9.data import StudyData, TrainingStream
from studies.p9ii import evaluate as p9iieval
from studies.p9ii import model as p9iimodel
from studies.p9ii.diagnostics import build_probe
from studies.p9ii.model import parameter_report
from studies.p9ii.train import Trainer, load_model_state, peak_rss, save_snapshot
from studies.p9ii.train import TrainJob as P9IIJob
from studies.p10s0 import core as s0core
from studies.p10s0 import evaluate as s0eval

from . import accounting, core
from .core import Cell

if TYPE_CHECKING:
    from torch import Tensor

    from arborlm.p4_model import Backbone

TRAINER_CHECK = re.compile(r"non-finite (loss|gradient norm|parameter) at update (\d+)")
SYNTHETIC_CORPUS = bytes((i * 7 + 3) % 256 for i in range(p9core.CORPUS_ROW_BYTES * 64))
EXCLUDED_FROM_IDENTITY = ("kind", "schema", "study", "label", "identity", "environment", "arm", "block", "celltype", "draw", "seed_index", "stage", "mode", "wall_seconds", "cpu_seconds")


class EnvironmentStop(RuntimeError):
    """An out-of-memory kill, a full disk or a file-system error: PAUSED — ENVIRONMENT, never a failed cell (section 12)."""


class SeedRefused(ValueError):
    """A seed set this role may not use (the study's own check: the identity gate re-uses P10-S0's rehearsal set read-only and nothing else outside the study)."""


def check_seed_set(role: str, name: str, *, identity_gate: bool = False) -> None:
    """REG: ``p10is0-draw-k`` and ``p10is0-reserve-k``; CAL: ``p10is0-cal-*``; REH: the rehearsal set; CHK: the pipeline-check set, and P10-S0's rehearsal set only for the identity gate (the declared re-use of the registry's section 4.6);
    TEST: ``p10is0-test-k`` (and P10-S0's test sets for the tiny identity test)."""
    if role == "REG":
        ok = bool(re.fullmatch(r"p10is0-(draw|reserve)-\d+", name))
    elif role == "CAL":
        ok = bool(re.fullmatch(r"p10is0-cal-\d(-repeat-\d)?", name))
    elif role == "REH":
        ok = name == "p10is0-rehearsal"
    elif role == "CHK":
        ok = name == "p10is0-check" or (identity_gate and name == s0core.REHEARSAL_SET.name)
    elif role == "TEST":
        ok = bool(re.fullmatch(r"p10is0-test-\d", name)) or (identity_gate and name.startswith("p10s0-test"))
    else:
        ok = False
    if not ok:
        raise SeedRefused(f"role {role!r} cannot use the {name!r} seed set")


# --- data and models ----------------------------------------------------------------------------------------------------------------
def build_data(seeds: p9core.SeedSet, corpus: bytes, facts: int, *, tiny: bool = False) -> StudyData:
    """The draw of one fact set. Real sizes are P9's defaults for ``main_trained = facts`` (as P10-S0's ``_build_data``); tiny sizes are for tests."""
    sizes = data_mod.DataSizes(main_trained=facts, unseen=64, lane_d_per_set=128) if tiny else data_mod.DataSizes(main_trained=facts)
    return data_mod.build_study_data(seeds, corpus, sizes=sizes)


def synthetic_backbone() -> "Backbone":
    return controls.synthetic_backbone(*p9core.PRIMARY_PARENT)


def build_model(cell: Cell, backbone: "Backbone", r1_seed: int, *, seed_rng: bool = True) -> Any:
    """``studies.p9ii.model.build_model(arm, slots, seed, backbone, r1_seed=...)`` itself, at any slot count."""
    return p9iimodel.build_model(cell.arm, cell.slots, cell.init_seed, backbone, r1_seed=r1_seed, seed_rng=seed_rng)


def diag_due(update: int, early: int = 64, late: int = 1024, switch: int = 4096) -> bool:
    """Probe records every ``early`` updates up to ``switch`` and every ``late`` after (section 4.3)."""
    return update % (early if update <= switch else late) == 0


# --- training ---------------------------------------------------------------------------------------------------------------------------
@dataclass
class Job:
    cell: Cell
    data: StudyData
    stream: TrainingStream
    backbone: "Backbone"
    out_dir: Path
    r1_seed: int
    target_seed: int = 0
    last_update: int = 0
    snapshots: tuple[int, ...] = ()
    init_snapshot: Path | None = None
    diag_early: int = 64
    diag_late: int = 1024
    diag_switch: int = 4096
    identity_gate: bool = False
    write_records: bool = True
    extra: dict[str, Any] = field(default_factory=dict)

    def to_p9ii(self) -> P9IIJob:
        """The ``studies.p9ii`` job the trainer reads (duck-typed cell: see the module docstring). ``mode`` is the trainer's own and is not read by ``Trainer``; this study's seed check is ``check_seed_set``."""
        return P9IIJob(
            cell=self.cell, hyper=s0core.HYPER, updates=self.last_update, mode="calibration", data=self.data, stream=self.stream, backbone=self.backbone, out_dir=self.out_dir,  # type: ignore[arg-type]
            init_seed=self.cell.init_seed, r1_seed=self.r1_seed, target_seed=self.target_seed, stream_seed=0, unit=s0core.UPDATES, stage=1, snapshots=self.snapshots, init_snapshot=self.init_snapshot,
            max_updates=self.last_update, diag_every=self.diag_early, rehearsal_phase=None, extra=dict(self.extra),
        )  # fmt: skip


@dataclass
class Segment:
    record: dict[str, Any]
    model: Any
    trainer: Any
    diverged: dict[str, Any] | None = None


def trainer_check(exc: BaseException, trainer: Trainer) -> tuple[str, int] | None:
    """Ruling 19: a divergence is exactly one of the trainer's three checks (a ValueError with that message, after the trainer's own flag was cleared). Nothing else is divergence."""
    if isinstance(exc, ValueError) and not all(trainer.all_finite.values()):
        m = TRAINER_CHECK.fullmatch(str(exc))
        if m:
            return m.group(1), int(m.group(2))
    return None


def set_aside_incomplete(out_dir: Path, start: int, marks: list[int]) -> list[Path]:
    """N1: a task killed mid-segment (cap, memory guard, disk pause, environment error) leaves this segment's log files, and perhaps a snapshot of a mark, with no completed train record. On a resume they are MOVED ASIDE, never deleted,
    into ``incomplete/<utc>/`` and the segment is run again from its snapshot; the logs are then opened exclusively as before. A segment whose train record exists is complete and is not touched (re-running it is refused by the exclusive open)."""
    if (out_dir / f"train_{start:08d}.json").is_file():
        return []
    stale = [p for p in (out_dir / f"updates_{start:08d}.jsonl", out_dir / f"diagnostics_{start:08d}.jsonl", *(out_dir / "snapshots" / f"u{m:07d}" for m in marks)) if p.exists()]
    moved = []
    if stale:
        dest = out_dir / "incomplete" / core.utc_stamp()
        dest.mkdir(parents=True, exist_ok=True)
        for p in stale:
            target = dest / (p.name if p.parent == out_dir else f"{p.parent.name}-{p.name}")
            p.rename(target)
            moved.append(target)
    return moved


def snapshot_update(snapshot: Path | None) -> int:
    return int(snapshot.name[1:]) if snapshot is not None else 0


def completed_segment(job: Job) -> "Segment | None":
    """N1 remainder: a task killed AFTER its segment reached the target (its train record exists) but before the result was written (during the evaluation) resumes by skipping straight to the evaluation: the finished segment's record is
    returned (``model`` and ``trainer`` are None: the snapshot on disk is the state) and nothing is trained, opened or set aside. The same for a segment with no work to do (the start is already the target), which must not open logs of its own.
    A diverged record is a finished segment too."""
    start = snapshot_update(job.init_snapshot)
    if job.write_records:
        path = job.out_dir / f"train_{start:08d}.json"
        if path.is_file():
            rec = core.read_record(path, "train")
            if rec.get("diverged") or int(rec["end_update"]) >= job.last_update:
                return Segment(rec, None, None, rec.get("diverged"))
    if start >= job.last_update > 0:
        return Segment({"status": "completed", "start_update": start, "end_update": start, "snapshot_sha256": {}, "diverged": None}, None, None, None)
    return None


def run_segment(job: Job) -> Segment:
    """Train from the job's snapshot (or from initialization) to ``last_update``, writing every per-update record and diagnostic to disk as it is produced. Snapshots at ``job.snapshots``. A divergence is returned in
    ``Segment.diverged`` (the registered scientific outcome of a learned cell, or of Stage R's rehearsal); a code error propagates; an environment error is raised as ``EnvironmentStop``."""
    check_seed_set(job.cell.role, job.data.seeds.name, identity_gate=job.identity_gate)
    done = completed_segment(job)
    if done is not None:
        return done
    started, cpu_started = time.monotonic(), time.process_time()
    model = build_model(job.cell, job.backbone, job.r1_seed)
    facts = int(job.stream.facts.shape[0])
    probe = build_probe(job.data, facts)
    trainer = Trainer(job.to_p9ii(), model, probe)
    if job.init_snapshot is not None:
        trainer.resume(job.init_snapshot)
    start = trainer.update
    marks = [m for m in sorted(set(job.snapshots)) if start < m <= job.last_update]
    report = parameter_report(model)
    update_log = diag_log = None
    if job.write_records:
        job.out_dir.mkdir(parents=True, exist_ok=True)
        set_aside_incomplete(job.out_dir, start, marks)
        update_log = (job.out_dir / f"updates_{start:08d}.jsonl").open("x", encoding="utf-8")
        diag_log = (job.out_dir / f"diagnostics_{start:08d}.jsonl").open("x", encoding="utf-8")
    process = psutil.Process()
    sampled_rss = 0
    hashes: dict[str, str] = {}
    diverged: dict[str, Any] | None = None
    if not trainer.anchor:
        trainer.anchor = {n: p.detach().clone() for n, p in trainer.named}
    try:
        for update in range(start + 1, job.last_update + 1):
            batch = job.stream.batch(update)
            try:
                record = trainer.step(batch)
            except ValueError as exc:
                found = trainer_check(exc, trainer)
                if found is None:
                    raise
                diverged = {"check": found[0], "update": found[1]}
                break
            sampled_rss = max(sampled_rss, int(process.memory_info().rss))
            if job.write_records and update % 1024 == 0:
                accounting.check_free(job.out_dir)  # R5: a full disk PAUSES (DiskPause is an environment condition)
            if update_log is not None:
                update_log.write(s0core.json_line(record) + "\n")
            if diag_due(update, job.diag_early, job.diag_late, job.diag_switch):
                diag = trainer.diagnose(batch)
                if diag_log is not None:
                    diag_log.write(s0core.json_line(diag) + "\n")
            if update in marks:
                h = save_snapshot(job.out_dir, update, model, trainer.optimizers, trainer.snapshot_extra(), write_json=False)
                hashes[str(update)] = h["model_sha256"]
    except accounting.DiskPause:
        raise
    except (MemoryError, OSError) as exc:
        raise EnvironmentStop(f"{type(exc).__name__}: {exc}") from exc
    finally:
        for log in (update_log, diag_log):
            if log is not None:
                log.flush()
                os.fsync(log.fileno())
                log.close()
    rec: dict[str, Any] = {
        **core.envelope("train"), "label": job.cell.label, "arm": job.cell.arm, "slots": job.cell.slots, "facts": facts, "init_seed": job.cell.init_seed, "seed_set": job.data.seeds.name, "start_update": start,
        "end_update": trainer.update, "planned_last_update": job.last_update, "snapshots": marks, "snapshot_sha256": hashes, "diverged": diverged,
        "status": "diverged" if diverged else "completed", "trainable_parameters": report["trainable"], "stored_parameters": report["stored"], "wall_seconds": time.monotonic() - started,
        "cpu_seconds": time.process_time() - cpu_started, "platform": accounting.platform_record(), "sampled_rss_bytes": sampled_rss, "peak_rss_bytes": peak_rss(), **job.extra,
    }  # fmt: skip
    if job.write_records:
        core.write_record(job.out_dir / f"train_{start:08d}.json", rec)
    return Segment(rec, model, trainer, diverged)


# --- evaluation ---------------------------------------------------------------------------------------------------------------------------
def evaluate_readout(
    cell: Cell, model: Any, data: StudyData, facts: int, update: int, *, backbone: "Backbone", rows: "Tensor", target_seed: int, swap_seed: int, frozen_loss: float | None = None, reference_swap: bool = False, chunked: bool = True
) -> dict[str, Any]:
    """P10-S0's evaluation record at a readout: ``studies.p9ii``'s record plus the read swap of both panels for a learned arm (P10-S0's ``read_swap``, called as it is). ``reference_swap`` adds the read swap for A6 too (Stage R's
    reference validity on condition 6 needs a_use of A6); P10-S0's own record has none, so the identity gate ignores that key. The record runs under ``torch.no_grad()`` (the underlying functions decorate themselves)."""
    with torch.no_grad():
        record = p9iieval.evaluate_readout(cell, model, data, facts, update, frozen_backbone=backbone, rows=rows, target_seed=target_seed, frozen_loss=frozen_loss, chunked=chunked)  # type: ignore[arg-type]
        record.update(core.envelope("eval"))
        record.update({"label": cell.label, "arm": cell.arm, "role": cell.role, "series": cell.series, "draw": cell.draw})
        record.pop("stage", None)
        if s0eval.has_read(cell.arm) or reference_swap:
            perm = s0eval.swap_permutation(data, facts, swap_seed)
            with p9iieval.eval_chunking(model, p9iieval.EVAL_CHUNK_ELEMENTS if chunked else 1 << 40):
                record["read_swap"] = {p: s0eval.read_swap(model, data, facts, p, perm) for p in s0core.PANELS}
            s0eval.check_swap_accuracy(record)
            record["read_swap"]["note"] = "a_use = facts answered correctly whose swapped prediction is not their answer, over all facts; condition 6 compares it with 0.95 x accuracy (ADR-0020 section 8.2)"
    return record


def evaluate_snapshot(cell: Cell, snapshot_dir: Path, data: StudyData, facts: int, update: int, *, backbone: "Backbone", rows: "Tensor", r1_seed: int, swap_seed: int, expected_sha256: str | None = None, reference_swap: bool = False) -> dict[str, Any]:
    """Load a snapshot (its hash must equal the train record's) and evaluate it."""
    if expected_sha256 is not None and file_sha256(snapshot_dir / "model.pt") != expected_sha256:
        raise ValueError(f"snapshot {snapshot_dir / 'model.pt'} does not match the hash recorded in the train record")
    model = build_model(cell, backbone, r1_seed, seed_rng=False)
    load_model_state(snapshot_dir, model)
    from studies.p9i.evaluate import next_byte_loss

    return evaluate_readout(cell, model, data, facts, update, backbone=backbone, rows=rows, target_seed=0, swap_seed=swap_seed, frozen_loss=next_byte_loss(backbone, rows), reference_swap=reference_swap)


def counts_of(record: Mapping[str, Any]) -> dict[str, Any]:
    """The integer counts and fields the labels read from an eval record (ruling 1): panels A and B, held-out H1 and H2 as (correct, n), and the rest as P10-S0's ``observation_from_eval`` reads them."""
    from studies.p9ii import classes as p9c

    from .labels import Obs

    base = p9c.observation_from_eval(record)
    pa, pb = record["panels"]["A"], record["panels"]["B"]
    sec = record["secondary"]
    swap = record.get("read_swap") or {}
    a_use_a = s0core.number((swap.get("A") or {}).get("a_use", float("nan")))
    a_use_b = s0core.number((swap.get("B") or {}).get("a_use", float("nan")))
    return {
        "obs": Obs((int(pa["correct"]), int(pa["facts"])), (int(pb["correct"]), int(pb["facts"])), (int(sec["H1"]["correct"]), int(sec["H1"]["facts"])), (int(sec["H2"]["correct"]), int(sec["H2"]["facts"])), base.dep_chance_a, base.dep_chance_b, base.leakage,
                    base.distinct_top1, base.largest_share, base.probe_facts, base.lm_rise, base.address_stability, a_use_a, a_use_b),
        "update": int(record["update"]),
    }  # fmt: skip
