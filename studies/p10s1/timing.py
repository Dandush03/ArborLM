# ruff: noqa: E501
"""P10S1 isolated timing and throughput (ADR-0021 sections 7.5 and 10.2). One process, nothing else of the project running: refused if the load average exceeds 1.0 at start,
retried up to three times within the cap; if never quiet the status is NOT MEASURED (for the throughput stage, THROUGHPUT NOT MEASURED, which does not make S1 incomplete).

* ``cpu_per_update``: process CPU seconds per training update of an arm at a slot count, the median of three runs of 256 updates after 32 warm-up updates (rehearsal: gives the
  measured cost for the matched-compute plan, section 5.4).
* ``throughput``: read-path queries per second at batch 1 and 128 for F-OQ, F-OQ-IVF, T-OQ, H8 and D-OQ at each slot count, five repeats; stable only if the coefficient of
  variation is at most 5%, otherwise UNSTABLE. RAM only, CPU only: not storage I/O.
"""

import os
import re
import statistics
import subprocess
import time
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

import torch
from torch.nn import functional as F

from studies.p9.data import StudyData, encode_identifiers

from . import core, index
from .model import DOQDense, H8Memory, P10S1Model
from .train import Trainer, TrainJob, job_model, peak_rss

if TYPE_CHECKING:
    from torch import Tensor

NOT_MEASURED = "NOT MEASURED"
OTHER_STUDY_PATTERN = re.compile(r"(?<![\w.])studies\.p10s[02](?![\w])")  # a live process of studies.p10s0 or studies.p10s2 (their stages are run as ``python -m studies.p10s0.stages ...``)
CONCURRENCY_STATEMENT = "no process of studies.p10s0 or studies.p10s2 stages was alive when this stage started (ADR-0021 section 25.12 item 4)"


class OtherStudyRunning(RuntimeError):
    """A study of the project (P10-S0 or P10-S2) has a live stage process: the timing preview, the isolated timing, the rehearsal and the registered stages refuse to start (section 25.12 item 4)."""


def running_commands() -> list[str]:
    """The command lines of every live process (``ps -axo command=``). Tests inject their own list instead of calling this."""
    out = subprocess.run(["ps", "-axo", "command="], capture_output=True, check=False, text=True).stdout  # noqa: S603, S607
    return [line.strip() for line in out.splitlines() if line.strip()]


def other_study_processes(commands: "list[str] | None" = None) -> list[str]:
    """The live command lines that belong to ``studies.p10s0`` or ``studies.p10s2`` (the list may be injected)."""
    return [c for c in (running_commands() if commands is None else commands) if OTHER_STUDY_PATTERN.search(c)]


class S0EvidenceRefused(RuntimeError):
    """The file named as the evidence that P10-S0's training has finished is not P10S0's registered stage manifest (ADR-0021 section 25.14 item 3)."""


def validate_s0_evidence(manifest: str | Path | None, refusal_record: str | Path | None = None) -> dict[str, Any]:
    """Validate ``--s0-training-manifest`` as the manifest of one of P10-S0's registered training stages (kind ``stage_manifest``, study ``P10S0``, mode ``registered``, a stage named ``train...``,
    status ``COMPLETE``) and bind it by hash. Where the manifest is the WX stage's (``train-wx``), S0's record of the probe's refusal is required too (a non-empty JSON object). An empty,
    incomplete or foreign file is refused. Returns the record that goes into the stage manifest."""
    import json

    from arborlm.io import file_sha256

    if not manifest or not Path(manifest).is_file():
        raise S0EvidenceRefused("refused: --s0-training-manifest (the manifest of P10-S0's last due registered training stage) is required: nothing here states that S0's training has finished without it")
    try:
        data = json.loads(Path(manifest).read_text())
    except (OSError, ValueError) as exc:
        raise S0EvidenceRefused(f"refused: {manifest} is not a JSON manifest ({exc})") from exc
    if not isinstance(data, dict) or data.get("kind") != "stage_manifest" or data.get("study") != "P10S0" or data.get("mode") != "registered":
        raise S0EvidenceRefused(f"refused: {manifest} is not a registered stage manifest of study P10S0")
    stage = str(data.get("stage", ""))
    if not stage.startswith("train"):
        raise S0EvidenceRefused(f"refused: {manifest} is the manifest of stage {stage!r}, not a training stage")
    if data.get("status") != "COMPLETE":
        raise S0EvidenceRefused(f"refused: the S0 stage {stage!r} has status {data.get('status')!r}, not COMPLETE")
    out: dict[str, Any] = {"s0_training_manifest": {"path": str(Path(manifest).resolve()), "sha256": file_sha256(Path(manifest)), "stage": stage, "run_id": data.get("run_id"), "finished_utc": data.get("finished_utc")}}
    if stage.endswith("wx") or "wx" in stage.split("-")[1:]:
        if not refusal_record or not Path(refusal_record).is_file():
            raise S0EvidenceRefused("refused: the WX training manifest needs S0's record of the probe's refusal (--s0-refusal-record)")
        try:
            rec = json.loads(Path(refusal_record).read_text())
        except (OSError, ValueError) as exc:
            raise S0EvidenceRefused(f"refused: the refusal record is not JSON ({exc})") from exc
        if not isinstance(rec, dict) or not rec:
            raise S0EvidenceRefused("refused: the refusal record is empty")
        out["s0_refusal_record"] = {"path": str(Path(refusal_record).resolve()), "sha256": file_sha256(Path(refusal_record))}
    elif refusal_record:
        if not Path(refusal_record).is_file():
            raise S0EvidenceRefused(f"refused: no S0 refusal record at {refusal_record}")
        out["s0_refusal_record"] = {"path": str(Path(refusal_record).resolve()), "sha256": file_sha256(Path(refusal_record))}
    return out


def concurrency_check(commands: "list[str] | None" = None) -> dict[str, Any]:
    """Refuse (``OtherStudyRunning``) while a process of ``studies.p10s0`` or ``studies.p10s2`` is alive; else the record that goes into the stage manifest."""
    alive = other_study_processes(commands)
    if alive:
        raise OtherStudyRunning(f"refused: {len(alive)} live process(es) of studies.p10s0 / studies.p10s2: {alive[:3]}; this stage starts after their stages have finished")
    return {"checked": True, "other_study_processes": [], "statement": CONCURRENCY_STATEMENT, "source": "injected" if commands is not None else "ps"}

THROUGHPUT_NOT_MEASURED = "THROUGHPUT NOT MEASURED"
UNSTABLE = "UNSTABLE"


def wait_for_quiet(load_fn: Callable[[], float] = lambda: os.getloadavg()[0], sleep: Callable[[float], None] = time.sleep, retries: int = core.TIMING_RETRIES, pause: float = 120.0) -> dict[str, Any]:
    """Section 7.5: refuse to start if the load average exceeds 1.0; retry until quiet up to three times; ``quiet`` False means NOT MEASURED."""
    loads: list[float] = []
    for attempt in range(retries + 1):
        load = float(load_fn())
        loads.append(load)
        if load <= core.LOAD_AVERAGE_MAX:
            return {"quiet": True, "attempts": attempt + 1, "load_averages": loads}
        if attempt < retries:
            sleep(pause)
    return {"quiet": False, "attempts": retries + 1, "load_averages": loads}


def cpu_seconds_per_update(job: TrainJob, *, warmup: int = core.TIMING_WARMUP_UPDATES, updates: int = core.TIMING_UPDATES, repeats: int = core.TIMING_REPEATS) -> dict[str, Any]:
    """Median over ``repeats`` of the process CPU seconds per update of ``updates`` consecutive updates after ``warmup`` warm-up updates (batches built inside the timed region, as in
    training). Nothing is written; the model is built here and discarded."""
    trainer = Trainer(job, job_model(job))
    u = 0
    for _ in range(warmup):
        u += 1
        trainer.step(job.stream.batch(u))
    runs, walls = [], []
    for _ in range(repeats):
        started, wall0 = time.process_time(), time.monotonic()
        for _ in range(updates):
            u += 1
            trainer.step(job.stream.batch(u))
        runs.append((time.process_time() - started) / updates)
        walls.append((time.monotonic() - wall0) / updates)
    return {"cpu_seconds_per_update": statistics.median(runs), "wall_seconds_per_update": statistics.median(walls), "runs": runs, "wall_runs": walls, "peak_rss_bytes": peak_rss(), "warmup_updates": warmup, "updates_per_run": updates}


# --- throughput ---------------------------------------------------------------------------------------------------------------------
def _read_path(model: P10S1Model, codes: "Tensor", ident: "Tensor") -> Callable[[int], None]:
    """The read path of an arm for a batch of ``b`` queries: select the slots (or hidden units), gather and combine the values, output projection (no backbone)."""
    mem = model.addition
    if isinstance(mem, DOQDense):
        def run_dense(b: int) -> None:
            hidden = F.gelu(F.linear(codes[:b], mem.w1, mem.b1), approximate="none")
            F.linear(hidden, mem.w2)

        return run_dense
    if isinstance(mem, H8Memory):
        table = mem.slot_table(ident)  # hashed once: the read is a lookup

        def run_hash(b: int) -> None:
            ids = table[:b]
            w = torch.full(ids.shape, 1.0 / core.TOP)
            F.linear((w[..., None] * mem.values[ids]).sum(-2), mem.wo)

        return run_hash

    def run_flat(b: int) -> None:
        ids, scores = mem.select_codes(codes[:b])
        w = scores.softmax(-1)
        F.linear((w[..., None] * mem.values[ids]).sum(-2), mem.wo)

    return run_flat


@torch.no_grad()
def measure_qps(fn: Callable[[int], None], batch: int, *, repeats: int = core.THROUGHPUT_REPEATS, min_seconds: float = 0.2) -> dict[str, Any]:
    """Queries per second at ``batch`` over ``repeats`` repeats (each at least ``min_seconds`` of loops); stable only if the coefficient of variation is at most 5%."""
    fn(batch)
    t = time.perf_counter()
    fn(batch)
    one = max(time.perf_counter() - t, 1e-7)
    iters = max(1, int(min_seconds / one))
    qps = []
    for _ in range(repeats):
        started = time.perf_counter()
        for _ in range(iters):
            fn(batch)
        qps.append(batch * iters / (time.perf_counter() - started))
    mean = statistics.fmean(qps)
    cv = statistics.pstdev(qps) / mean if mean > 0 else float("inf")
    return {"qps": qps, "median_qps": statistics.median(qps), "cv": cv, "stable": cv <= core.THROUGHPUT_CV_MAX, "label": "STABLE" if cv <= core.THROUGHPUT_CV_MAX else UNSTABLE, "iterations_per_repeat": iters}


def throughput_record(model: P10S1Model, data: StudyData, facts: int, seeds: Any, arm_label: str | None = None) -> dict[str, Any]:
    """Throughput of a trained cell's read path at batch 1 and 128 (``arm_label`` F-OQ-IVF reads F-OQ's keys through the index)."""
    ident = encode_identifiers(data.facts.ident[:facts])
    batch = max(core.THROUGHPUT_BATCHES)
    ident = ident[:batch]
    codes = model.addition.codes.of_codes(ident) if isinstance(model.addition, DOQDense) else _codes(model, ident)
    mem_model = model
    if arm_label == "F-OQ-IVF":
        idx = index.build_index(model.addition.keys.detach(), core.index_seed(seeds))
        import copy

        mem_model = copy.deepcopy(model)
        mem_model.addition = index.IVFMemory(model.addition, idx)
    fn = _read_path(mem_model, codes, ident)
    return {str(b): measure_qps(fn, b) for b in core.THROUGHPUT_BATCHES}


def _codes(model: P10S1Model, ident: "Tensor") -> "Tensor":
    from .model import OracleCodes

    if model.arm in ("F-OQ", "T-OQ"):
        return OracleCodes(model.r1_seed).of_codes(ident)
    return torch.zeros(ident.shape[0], core.KEY_WIDTH)  # H8 reads by identifier, not by code
