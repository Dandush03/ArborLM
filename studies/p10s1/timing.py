# ruff: noqa: E501
"""P10S1 isolated timing and throughput (ADR-0021 sections 7.5 and 10.2). One process, nothing else of the project running: refused if the load average exceeds 1.0 at start,
retried up to three times within the cap; if never quiet the status is NOT MEASURED (for the throughput stage, THROUGHPUT NOT MEASURED, which does not make S1 incomplete).

* ``cpu_per_update``: process CPU seconds per training update of an arm at a slot count, the median of three runs of 256 updates after 32 warm-up updates (rehearsal: gives the
  measured cost for the matched-compute plan, section 5.4).
* ``throughput``: read-path queries per second at batch 1 and 128 for F-OQ, F-OQ-IVF, T-OQ, H8 and D-OQ at each slot count, five repeats; stable only if the coefficient of
  variation is at most 5%, otherwise UNSTABLE. RAM only, CPU only: not storage I/O.
"""

import os
import statistics
import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

import torch
from torch.nn import functional as F

from studies.p9.data import StudyData, encode_identifiers

from . import core, index
from .model import DOQDense, H8Memory, P10S1Model
from .train import Trainer, TrainJob, job_model

if TYPE_CHECKING:
    from torch import Tensor

NOT_MEASURED = "NOT MEASURED"
THROUGHPUT_NOT_MEASURED = "THROUGHPUT NOT MEASURED"
UNSTABLE = "UNSTABLE"


def wait_for_quiet(load_fn: Callable[[], float] = lambda: os.getloadavg()[0], sleep: Callable[[float], None] = time.sleep, retries: int = core.TIMING_RETRIES, pause: float = 30.0) -> dict[str, Any]:
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
    runs = []
    for _ in range(repeats):
        started = time.process_time()
        for _ in range(updates):
            u += 1
            trainer.step(job.stream.batch(u))
        runs.append((time.process_time() - started) / updates)
    return {"cpu_seconds_per_update": statistics.median(runs), "runs": runs, "warmup_updates": warmup, "updates_per_run": updates}


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
