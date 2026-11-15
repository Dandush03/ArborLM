# ruff: noqa: E501
"""P10S2 stage drivers: the stage functions (shared by the dry stage, the rehearsal and the registered stages), the fixed registered launch interface, the pre-freeze commands and the command line.

* ``dry``: a tiny synthetic end-to-end run on stand-ins and test seeds (gates, training of the whole registry, scoring, assembled composites, retrieval, routers, independent recomputation, analysis,
  report). It is not calibration, pilot, rehearsal or a registered stage and produces no result.
* ``registered <name> --run-dir D --freeze-commit C --caps studies/p10s2/freeze/stage_caps.json``: one registered stage by name. The launch scripts pass exactly this. There is no other argument: not a
  repository (the code that runs is the code checked), not a caps file (only the frozen table's path is accepted), not a device, a design, a data directory or a calibration record: all come from the
  frozen plan. A registered stage refuses unless the working tree is clean, the freeze commit is the commit that added the plan and an ancestor of HEAD, the frozen paths equal their content at that
  commit, every identity in the plan holds, a committed run decision exists, the stage has a cap for the plan's design, the study ledger (which holds P and every other stage's charge) has room for
  this stage's cap AND the reserved analysis and report caps, the frozen device is usable, and its predecessor has completed (gates all passed, then train, evaluate, timing, recompute, analysis,
  report); a stage whose own record exists is never run again and its outputs are write-once.
* ``calibrate``, ``prefreeze-gates``, ``rehearse``, ``raise-cap`` and ``freeze``: the pre-freeze procedure on rehearsal and calibration seeds, all charged to the one study ledger.

Registered stages: gates (the second gates stage on registered seeds), train, evaluate, timing, recompute (the independent CPU recomputation, charged), analysis, report. Every stage runs under a
``StageGuard``: a wall-clock deadline (its frozen cap), a sampled memory watchdog (8 GiB per worker; resident set and MPS memory), and its peak is recorded. Nothing here runs a registered stage unless
invoked through the registered command with a recorded freeze.
"""

import argparse
import contextlib
import ctypes
import json
import sys
import threading
import time
from collections.abc import Callable, Iterator, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import torch

from arborlm.io import file_sha256, read_json, write_json

from . import (
    analysis,
    budget,
    cells,
    core,
    freeze,
    gates,
    output,
    recompute,
    report,
    standins,
    train,
)
from .ledger import Ledger, LedgerRefused
from .prefreeze import prefreeze_summary
from .registry import registry, replicate_cells
from .world import World
from .worldio import DataBundle, RunConfig, build_world, read_bundle, write_bundle

REGISTERED_STAGES = budget.REGISTERED_STAGES
GIB = 2**30
GATE_NAMES = tuple(f"G{i}" for i in range(1, 10))


class StageRefused(RuntimeError):
    """A registered stage refuses to start (the P9-II convention): nothing is started and nothing is re-run with changed settings."""


class CapReached(RuntimeError):
    """A stage cap was reached: the stage is not continued (the label becomes INCOMPLETE)."""


class MemoryLimitExceeded(RuntimeError):
    """The sampled memory exceeded the per-worker limit: the stage is stopped and a memory record is written."""


def _utc() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class Deadline:
    def __init__(self, cap_seconds: float | None) -> None:
        self.cap = cap_seconds
        self.t0 = time.perf_counter()

    def expired(self) -> bool:
        return self.cap is not None and time.perf_counter() - self.t0 > self.cap

    def reason(self) -> str | None:
        return f"the stage cap of {self.cap:.1f} s was reached" if self.expired() and self.cap is not None else None

    def check(self, what: str) -> None:
        if self.expired() and self.cap is not None:
            raise CapReached(f"the stage cap of {self.cap:.1f} s was reached before {what}")


@contextlib.contextmanager
def _armed(deadline: Deadline | None) -> Iterator[None]:
    """While a stage function runs, the deadline is asked on every update of every cell (``train.STOP``): a cap stops the cell running, not only the next replicate."""
    if deadline is None or deadline.cap is None:
        yield
        return
    train.STOP.hooks.append(deadline.reason)
    try:
        yield
    finally:
        if deadline.reason in train.STOP.hooks:
            train.STOP.hooks.remove(deadline.reason)


class StageGuard:
    """A stage's guard: a sampled watchdog thread (every ``watchdog_interval_seconds``) that records the peak of the resident set and of MPS memory, stops the stage when the sampled memory exceeds the
    per-worker limit (``memory_exceeded``), and stops it when its wall-clock cap is reached. A stop sets ``train.STOP`` (every cell ends ``failed`` with the reason) and interrupts the main thread (a long
    scoring call ends as soon as it returns to Python). On exit the interrupt is turned into ``CapReached`` or ``MemoryLimitExceeded``.

    The interrupt is an asynchronous ``KeyboardInterrupt`` raised in the thread that entered the guard (``PyThreadState_SetAsyncExc``), not a simulated SIGINT: a process launched in the background (``&``,
    ``nohup``) ignores SIGINT, and ``_thread.interrupt_main`` is then a silent no-op, which would have made every cap and memory limit decorative."""

    def __init__(self, name: str, *, cap_seconds: float | None = None, memory_limit_bytes: int | None = None, interval: float | None = None) -> None:
        self.name = name
        self.cap = cap_seconds
        self.limit = memory_limit_bytes
        self.interval = float(core.CFG["budget"]["watchdog_interval_seconds"]) if interval is None else interval
        self.peak = 0
        self.peaks: dict[str, int] = {}
        self.exceeded = False
        self.stop_reason: str | None = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._t0 = 0.0
        self._owner = threading.get_ident()

    def sample(self, enforce: bool = True) -> None:
        m = train.process_memory_bytes()
        self.peaks = {k: max(self.peaks.get(k, 0), v) for k, v in m.items()}
        self.peak = max(self.peak, m["max"])
        if enforce and self.limit is not None and m["max"] > self.limit and self.stop_reason is None:
            self.exceeded = True
            self._request(f"memory limit: {m['max'] / GIB:.2f} GiB sampled, limit {self.limit / GIB:.2f} GiB")

    def _request(self, reason: str) -> None:
        self.stop_reason = reason
        train.STOP.set(reason)
        if threading.get_ident() != self._owner:  # raised from the watchdog thread in the stage's thread; from the stage's own thread (a sample) it is left to the stop flag
            ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_ulong(self._owner), ctypes.py_object(KeyboardInterrupt))

    def _loop(self) -> None:
        while not self._stop.wait(self.interval):
            self.sample()
            if self.stop_reason is not None:
                return
            if self.cap is not None and time.perf_counter() - self._t0 > self.cap:
                self._request(f"the stage cap of {self.cap:.1f} s was reached")
                return

    def __enter__(self) -> "StageGuard":
        self._owner = threading.get_ident()
        train.STOP.clear()
        self._t0 = time.perf_counter()
        self.sample(enforce=False)
        if self.interval > 0:
            self._thread = threading.Thread(target=self._loop, name=f"guard-{self.name}", daemon=True)
            self._thread.start()
        return self

    def __exit__(self, et: Any, ev: Any, tb: Any) -> None:
        self._stop.set()
        late = False
        try:
            if self._thread is not None:
                self._thread.join()
            ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_ulong(self._owner), None)  # clear a stop request that was raised but not yet delivered
            with contextlib.suppress(Exception):
                self.sample(enforce=False)
        except KeyboardInterrupt:
            late = True  # the stop request landed while the guard was closing
        reason = self.stop_reason
        train.STOP.clear()
        if (et is KeyboardInterrupt or late) and reason is not None:
            raise (MemoryLimitExceeded(reason) if self.exceeded else CapReached(reason)) from None

    def record(self) -> dict[str, Any]:
        return {"stage": self.name, "peak_bytes": self.peak, "peak_components_bytes": self.peaks, "limit_bytes": self.limit, "memory_exceeded": self.exceeded, "stop_reason": self.stop_reason, "wall_seconds": time.perf_counter() - self._t0, "sampled_every_seconds": self.interval, "peak_sources": "max of the resident-set peak and the MPS driver and allocator memory (torch.mps) where MPS was used"}


@contextlib.contextmanager
def scoring_environment() -> Iterator[dict[str, Any]]:
    """The same thread count (six, section 10.2) and deterministic-algorithms setting in evaluate, recompute and the gates stage (audit B m3: they differed, which makes a read with two reads at one position
    differ bitwise between evaluation and recomputation by construction). The previous settings are restored."""
    threads, det, warn = torch.get_num_threads(), torch.are_deterministic_algorithms_enabled(), torch.is_deterministic_algorithms_warn_only_enabled()
    torch.set_num_threads(int(core.CFG["budget"]["timing_threads"]))
    torch.use_deterministic_algorithms(True)
    try:
        yield {"threads": torch.get_num_threads(), "deterministic_algorithms": True}
    finally:
        torch.use_deterministic_algorithms(det, warn_only=warn)
        torch.set_num_threads(threads)


def record(path: Path, obj: Any, *, overwrite: bool = False) -> None:
    """A stage record. Outputs are write-once: an existing file is never replaced (audit B M2), except where ``overwrite`` is stated."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        raise FileExistsError(f"{path} exists: stage outputs are write-once")
    write_json(path, core.jsonable(obj))


def say(text: str, stream: Any = None) -> None:
    """One line to a stream, through the printer that puts any guarded word under the oracle-assisted line."""
    output.emit([text], stream if stream is not None else sys.stdout)


# --- stage functions ---------------------------------------------------------------------------------------------------------------------------
def gate_inputs(world: World, prefreeze: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """G1 at stream level (the replicate draws of this run's seeds against the panels) and G3 from the pre-freeze record's qualification. The data step checked G1 on the pools; the gates stage checks the
    streams, where a registered replicate seed may be used."""
    from .data import gate_g1

    g1 = gate_g1(world.partition, world.streams, {c: [x.target for s in world.streams for x in s.t[c]] for c in core.TASKS})
    q = prefreeze.get("qualification", {})
    return g1, {"ok": bool(q.get("ok", False)), "outcome": q.get("outcome"), "failed": q.get("failed", [])}


def stage_gates(world: World, run_dir: Path, plan: core.SeedPlan, *, g1: Mapping[str, Any], g3: Mapping[str, Any], equivalence_record: dict[str, Any] | None, file_manifest: Mapping[str, Mapping[str, str]] | None = None, root: Path | None = None, updates: int | None = None, require_mps: bool = False) -> dict[str, Any]:
    with scoring_environment():
        out = gates.run_gates(world, plan, g1=g1, g3=g3, equivalence_record=equivalence_record, file_manifest=file_manifest, root=root, updates=updates, require_mps=require_mps)
    from .data import replicate_overlap

    out["replicate_overlap"] = replicate_overlap(world.streams)  # the share of training items common to each pair of replicates (section 5.2); no part of any gate
    record(run_dir / "gates.json", out)
    return out


def _snapshot_manifest(snap_dir: Path, label: str) -> dict[str, Any] | None:
    safe = label.replace("/", "__").replace("@", "_at_")
    p = snap_dir / f"{safe}.manifest.json"
    return json.loads(p.read_text()) if p.exists() else None


def _recover_records(r: int, snap_dir: Path, error: str) -> dict[str, dict[str, Any]]:
    """After an exception out of a replicate's training (anything but a failure inside a cell, which ``train_arm`` keeps as a failed record), the replicate's records are rebuilt from what exists: a cell with
    a snapshot is completed (its training curve is not kept), every other cell is failed with the error text. Nothing is retried."""
    out: dict[str, dict[str, Any]] = {}
    for cell in replicate_cells(r):
        m = _snapshot_manifest(snap_dir, cell.label)
        if m is not None:
            out[cell.label] = {"label": cell.label, "status": "completed", "train": [], "snapshots": {cell.label: m}, "note": f"record rebuilt after an exception ({error}); the training curve was not kept"}
        else:
            out[cell.label] = {"label": cell.label, "status": "failed", "train": [{"status": "failed", "error": error}], "snapshots": {}}
    return out


def stage_train(world: World, run_dir: Path, deadline: Deadline | None = None) -> dict[str, Any]:
    """Training of every cell of every replicate. A cell that fails (a non-finite loss, an operation or device error, a stage cap, the memory limit) keeps its record and stops only the cells that depend on
    it; the replicate's other records survive (``train.train_arm`` never raises out of a cell, and an exception anywhere else rebuilds the replicate's records from the snapshots written so far)."""
    stopped: list[str] = []
    with _armed(deadline):
        for r in range(world.replicates):
            try:
                if deadline is not None:
                    deadline.check(f"training replicate {r}")
            except CapReached as e:
                stopped.append(str(e))
                break
            try:
                recs = cells.train_replicate(world, r, run_dir / "snapshots")
            except KeyboardInterrupt:
                if train.STOP.reason is None:
                    raise
                recs = _recover_records(r, run_dir / "snapshots", f"stopped: {train.STOP.reason}")
            except Exception as e:  # noqa: BLE001
                recs = _recover_records(r, run_dir / "snapshots", f"{type(e).__name__}: {e}")
            record(run_dir / "train" / f"r{r}.json", recs)
            if train.STOP.reason is not None:
                last = next((c for c in reversed(replicate_cells(r)) if recs.get(c.label, {}).get("status") == "failed"), None)
                stopped.append(f"replicate {r}: {train.STOP.reason}" + (f" (the last failed cell is {last.label})" if last else ""))
                break
    record(run_dir / "train" / "stopped.json", stopped)
    return {"stopped": stopped}


def _load_train(run_dir: Path, r: int) -> dict[str, dict[str, Any]]:
    p = run_dir / "train" / f"r{r}.json"
    return read_json(p) if p.exists() else {}


def stage_evaluate(world: World, run_dir: Path, deadline: Deadline | None = None, *, subdir: str = "evaluate") -> dict[str, Any]:
    """Scoring on CPU from the snapshots: Stage 0 and the stored teacher scores, then per replicate the 18 cells, the assembled composites, the retrieval baselines and the router lane. Thread count and
    deterministic setting are those of the recomputation (``scoring_environment``). An exception while scoring a replicate keeps every other replicate's record."""
    stopped: list[str] = []
    with scoring_environment(), _armed(deadline):
        base = cells.stage0_scores(world)
        record(run_dir / subdir / "baseline.json", base)
        teacher_own = {c: base["teacher"].get("E_" + c, {}).get("mean") for c in core.TASKS}  # each teacher's own score on its panel (the ensemble must reproduce it)
        for r in range(world.replicates):
            rep: dict[str, Any]
            try:
                if deadline is not None:
                    deadline.check(f"scoring replicate {r}")
                tr = _load_train(run_dir, r)
                routers = cells.build_routers(world, r)
                scored = cells.score_replicate(world, r, run_dir / "snapshots", tr, routers)
                ens_oracle = {c: evaluate_mean_teacher(world, c) for c in core.TASKS}
                ens_learned = ensemble_under_router(world, routers[("A", "B")][0])
                all_first = all(f"r{r}/{g}/{v}" in tr and tr[f"r{r}/{g}/{v}"]["status"] == "completed" for g, v in (("ST1", "AB"), ("ST1", "BA"), ("LORA1", "AB"), ("LORA1", "BA")))
                rep = {
                    "cells": scored, "assembled": cells.assembled_scores(world, r, run_dir / "snapshots") if all_first else {},
                    "retrieval": cells.retrieval_scores(world, r), "routers": cells.router_record(world, r, routers), "ensemble": {"oracle": ens_oracle, "teacher_own": teacher_own, "learned_router": ens_learned},
                }  # fmt: skip
            except CapReached as e:
                stopped.append(str(e))
                break
            except KeyboardInterrupt:
                if train.STOP.reason is None:
                    raise
                stopped.append(f"scoring replicate {r}: {train.STOP.reason}")
                break
            except Exception as e:  # noqa: BLE001
                rep = {"cells": {}, "error": f"scoring of replicate {r} failed: {type(e).__name__}: {e}"}
            record(run_dir / subdir / f"r{r}.json", rep)
    record(run_dir / subdir / "stopped.json", stopped)
    return {"stopped": stopped}


def ensemble_under_router(world: World, router: Any) -> dict[str, float] | None:
    """The two teachers behind the learned keyword router: an item goes to the teacher the router names from the prompt (a wrongly routed item, or one routed to "none", scores 0)."""
    from . import evaluate, retrieval

    ctx = world.ctx
    refs = {c: ctx.panels["E_" + c].refs for c in core.TASKS}
    outs: dict[str, list[str]] = {}
    for c in core.TASKS:
        o = world.teacher_outputs.get(c, {}).get("E_" + c)
        if o is None:
            return None
        outs[c] = o
    decisions = {c: [(evaluate.route_for(ctx, ex, router, "learned") or ["none"])[0] for ex in ctx.panels["E_" + c].examples] for c in core.TASKS}
    return retrieval.ensemble_scores(outs, refs, lambda c, i: decisions[c][i])


def evaluate_mean_teacher(world: World, cap: str) -> float | None:
    """The oracle-routed ensemble's score on capability ``cap``: every item goes to its own capability's teacher through the route function, scored by the same chrF code. It must equal the teacher's own
    score (a difference is ENGINEERING-FAILURE, section 11.3)."""
    from . import retrieval

    ctx = world.ctx
    refs = {c: ctx.panels["E_" + c].refs for c in core.TASKS}
    outs: dict[str, list[str]] = {}
    for c in core.TASKS:
        o = world.teacher_outputs.get(c, {}).get("E_" + c)
        if o is None:
            return None
        outs[c] = o
    scores = retrieval.ensemble_scores(outs, refs, lambda c, _i: c)
    return scores[cap]


def stage_timing(world: World, run_dir: Path, items: int | None = None, deadline: Deadline | None = None) -> dict[str, Any]:
    """The timing benchmark, separate from training: after all training, one process, CPU, six threads, median of the registered repetitions on a fixed subset of each panel. Descriptive only; no
    latency, throughput, storage or efficiency claim. The thread count of the process is restored afterwards (a leaked setting would change the bit-level behaviour of everything that runs later)."""
    from . import evaluate
    from .world import load_arm

    n_items = items if items is not None else core.CFG["budget"]["timing_items"]
    ctx = world.ctx
    previous = torch.get_num_threads()
    torch.set_num_threads(int(core.CFG["budget"]["timing_threads"]))
    try:
        out: dict[str, Any] = {"threads": torch.get_num_threads(), "items_per_panel": n_items, "type": "measured, descriptive; no efficiency claim"}
        snap_dir = run_dir / "snapshots"
        for label in ("r0/ST1/AB", "r0/MAF/AB", "r0/LORA1/AB"):
            if not (snap_dir / (label.replace("/", "__") + ".pt")).exists():
                continue
            arm = load_arm(world, 0, snap_dir, label)
            for name, p in ctx.panels.items():
                if deadline is not None:
                    deadline.check(f"timing {label} on {name}")
                idx = list(range(min(n_items, len(p.examples))))
                out[f"{label}/{name}"] = evaluate.timing_benchmark(lambda arm=arm, p=p, idx=idx: evaluate.score_panel(ctx, arm, p, indices=idx))  # type: ignore[misc]
    finally:
        torch.set_num_threads(previous)
    record(run_dir / "timing.json", out)
    return out


def stage_recompute(world: World, run_dir: Path, deadline: Deadline | None = None) -> dict[str, Any]:
    """The independent recomputation of every score from the snapshots, on CPU, with deterministic algorithms, in a separate pass (``recompute/``). With the frozen scoring code every score must be
    bit-identical; the comparison and the label rule are in ``recompute.outcome_under_recomputation``."""
    return stage_evaluate(world, run_dir, deadline, subdir="recompute")


# --- assembling the study record and the outcome ------------------------------------------------------------------------------------------------
def gates_problems(gates_record: Mapping[str, Any]) -> list[str]:
    """A missing gates record, or a gate with no record, is never "all passed" (audit B M2)."""
    if not gates_record:
        return ["the gates record is missing: the gates cannot be read as passed"]
    return [f"gate {g} has no record in the gates record" for g in GATE_NAMES if g not in gates_record]


def assemble_study(run_dir: Path, design: Mapping[str, Any], prefreeze: Mapping[str, Any], gates_record: Mapping[str, Any] | None, *, subdir: str = "evaluate", extra_incomplete: Sequence[str] = (), extra_engineering: Sequence[str] = ()) -> dict[str, Any]:
    n = int(design["replicates"])
    reps = []
    incomplete = list(extra_incomplete)
    for r in range(n):
        p = run_dir / subdir / f"r{r}.json"
        rep = read_json(p) if p.exists() else {"cells": {}}
        if rep.get("error"):
            incomplete.append(str(rep["error"]))
        reps.append(rep)
    base_p = run_dir / subdir / "baseline.json"
    for kind in ("train", subdir):
        sp = run_dir / kind / "stopped.json"
        if sp.exists():
            incomplete += [f"a cap stopped the {kind} stage: {m}" for m in read_json(sp)]
    return {"design": dict(design), "prefreeze": dict(prefreeze), "gates": dict(gates_record or {}), "baseline": read_json(base_p) if base_p.exists() else {}, "replicates": reps, "incomplete": incomplete, "engineering": list(extra_engineering)}


def _memory_exceeded(run_dir: Path, stage: str) -> bool:
    p = run_dir / "memory" / f"{stage}.json"
    return bool(read_json(p).get("memory_exceeded")) if p.exists() else False


def stage_analysis(run_dir: Path, design: Mapping[str, Any], prefreeze: Mapping[str, Any], mode: str = "frozen-code") -> dict[str, Any]:
    """Classes, label, annotations and the recomputation rule over every recomputed quantity. Write-once. The only seed this stage may draw is the bootstrap seed 220906 (G9, the lead's ruling); the record of
    what it drew is written beside the outcome."""
    out_path = run_dir / "outcome.json"
    if out_path.exists():
        raise FileExistsError(f"{out_path} exists: the outcome is write-once")
    seeds_before = len(core.seed_record())  # a registered analysis process starts with an empty record; the dry stage's process does not
    gp = run_dir / "gates.json"
    gates_record = read_json(gp) if gp.exists() else {}
    problems = gates_problems(gates_record)
    reg = assemble_study(run_dir, design, prefreeze, gates_record, extra_engineering=problems)
    n = int(design["replicates"])
    rec_study = None
    if (run_dir / "recompute" / "baseline.json").exists() and all((run_dir / "recompute" / f"r{r}.json").exists() for r in range(n)):
        rec_study = assemble_study(run_dir, design, prefreeze, gates_record, subdir="recompute", extra_engineering=problems)
    outcome = recompute.outcome_under_recomputation(reg, rec_study, mode, memory_exceeded=_memory_exceeded(run_dir, "recompute"))
    seeds = gates.analysis_seed_check(core.seed_record()[seeds_before:])
    record(run_dir / "seeds" / "analysis.json", seeds)
    if not seeds["ok"]:
        raise RuntimeError("G9 in the analysis stage: " + "; ".join(seeds["problems"]))
    output.write_record(out_path, analysis.outcome_record(outcome))
    return outcome


def stage_report(run_dir: Path) -> str:
    if (run_dir / "REPORT.md").exists():
        raise FileExistsError(f"{run_dir / 'REPORT.md'} exists: the report is write-once")
    rec = read_json(run_dir / "outcome.json")
    outcome = rec["outcome"]
    gp = run_dir / "gates.json"
    overlap = read_json(gp).get("replicate_overlap", {}) if gp.exists() else {}
    extra = [report.overlap_line(overlap)] if overlap else []
    text = report.render_report(outcome, extra=extra)
    output.write_text(run_dir / "REPORT.md", text)
    output.emit(report.summary_lines(outcome))
    return text


# --- the dry stage ------------------------------------------------------------------------------------------------------------------------------
def manifest_gates(directory: Path) -> dict[str, dict[str, str]]:
    """The digests recorded at creation (``manifest.json``), for G7. They are read from the manifest, never computed from the files they are compared with (audit A: a check against a manifest computed from
    the same files cannot fail)."""
    return {n: {"algo": spec["algo"], "digest": spec["digest"]} for n, spec in json.loads((directory / "manifest.json").read_text())["files"].items()}


def dry(run_dir: Path, replicates: int = 2, updates: int | None = None, gates_updates: int = 3) -> dict[str, Any]:
    """Tiny synthetic end to end on stand-ins and test seeds. Every number is a mechanics check, not a result. It has its own ledger (``run_dir/ledger.jsonl``) and never touches the study ledger."""
    core.reset_seed_record()
    ledger = Ledger(run_dir / "ledger.jsonl")
    with ledger.measure("datagen", process="dry: synthetic data generation and partition"):
        bundle, pre = standins.build_synthetic_bundle(replicates)
        bundle.extra["equivalence"] = _dry_equivalence(bundle, RunConfig.dry(updates).layer)  # what the data-generation step records against its reference
        data_dir = run_dir / "data"
        write_bundle(bundle, data_dir)
        bundle = read_bundle(data_dir)  # hash-checked load
        world = build_world(bundle, "test", replicates, RunConfig.dry(updates))
    plan0 = core.SeedPlan("test", 0)
    streams_g1, g3 = gate_inputs(world, pre)
    with ledger.measure("gates-rehearsal", process="dry: gates"):
        g = stage_gates(world, run_dir, plan0, g1=streams_g1, g3=g3, equivalence_record=bundle.extra["equivalence"], file_manifest=manifest_gates(data_dir), root=data_dir, updates=gates_updates)
    with ledger.measure("train", process="dry: training"):
        stage_train(world, run_dir)
    with ledger.measure("evaluate", process="dry: scoring"):
        stage_evaluate(world, run_dir)
    with ledger.measure("timing", process="dry: timing benchmark"):
        stage_timing(world, run_dir, items=3)
    with ledger.measure("recompute", process="dry: independent recomputation"):
        stage_recompute(world, run_dir)
    design = {"replicates": replicates, "updates": world.updates, "synthetic": True}
    prefreeze = prefreeze_summary(pre)
    with ledger.measure("analysis", process="dry: analysis"):
        outcome = stage_analysis(run_dir, design, prefreeze)
    with ledger.measure("report", process="dry: report"):
        stage_report(run_dir)
    core_record = {"seeds": core.seed_gate(core.seed_record(), planned_mode="test"), "ledger": ledger.summary()}
    record(run_dir / "run_record.json", {"gates_ok": g["ok"], **core_record})
    return {"gates": g, "outcome": outcome, "run_record": core_record}


def _dry_equivalence(bundle: DataBundle, layer: int) -> dict[str, Any]:
    """A reference stand-in written independently of the student (explicit loops, Hugging Face naming) records the equivalence result, as the data-generation step would with the real reference."""
    from .equivalence import build_record
    from .model import build_student, export_hf_state_dict, load_plain_state
    from .reference_standin import ReferenceLlama

    student = build_student(bundle.cfg)
    load_plain_state(student, bundle.student_state)
    ref = ReferenceLlama(bundle.cfg, export_hf_state_dict(student))
    g = core.seeded_generator(core.SEEDS["test_low"] + 700, "dry equivalence text", "test")
    ids = torch.randint(0, bundle.cfg.vocab, (1, 32), generator=g)
    vec = torch.randn(bundle.cfg.width, generator=g)
    prompts = [[int(x) for x in torch.randint(0, bundle.cfg.vocab, (6,), generator=g).tolist()] for _ in range(3)]
    return build_record(student, ref, ids, vec, layer, prompts, 5)


# --- registered stages ---------------------------------------------------------------------------------------------------------------------------
def load_plan(repo: Path) -> dict[str, Any]:
    return freeze.load_plan(repo)


def stage_record_path(run_dir: Path, name: str) -> Path:
    return run_dir / "stages" / f"{name}.json"


def check_code_location(repo: Path) -> None:
    """The code that runs must be the code that is checked: the study package and the library lie under the checked repository (audit B M1: ``--repo`` pointed every check at another tree)."""
    import arborlm

    for mod, name in ((core, "studies.p10s2"), (arborlm, "arborlm")):
        f = Path(mod.__file__ or "").resolve()
        if not f.is_relative_to(repo.resolve()):
            raise StageRefused(f"refused: {name} is imported from {f}, which is not under the checked repository {repo}")


def require_order(run_dir: Path, name: str) -> None:
    """Stage order and write-once: the stage's own record must not exist; its predecessor's record must (completed or stopped); train needs the gates record with every gate present and passed."""
    own = stage_record_path(run_dir, name)
    if own.exists():
        raise StageRefused(f"refused: stage {name} already has a record ({own}; status {read_json(own).get('status')}): a stage is run once and never re-run with changed settings")
    i = REGISTERED_STAGES.index(name)
    if i > 0:
        prev = REGISTERED_STAGES[i - 1]
        pr = stage_record_path(run_dir, prev)
        if not pr.exists():
            raise StageRefused(f"refused: stage {name} requires the completion record of {prev} ({pr}), which does not exist")
        if read_json(pr).get("status") not in ("completed", "stopped"):
            raise StageRefused(f"refused: stage {prev} ended with status {read_json(pr).get('status')!r}; stage {name} does not run after it")
    if name == "train":
        gp = run_dir / "gates.json"
        if not gp.exists():
            raise StageRefused("refused: no gates record: a missing gates record is never read as all gates passed")
        g = read_json(gp)
        bad = [k for k in GATE_NAMES if k not in g or not g[k].get("ok")]
        if bad or not g.get("ok"):
            raise StageRefused(f"refused: the second gates stage did not pass ({', '.join(bad) or 'ok is not true'}): a failed gate stops the run")


def reserved_seconds(caps: Mapping[str, Mapping[str, float]], name: str, n: int, u: int) -> float:
    """The analysis and report caps are reserved while an earlier stage runs, so that an overrun cannot lock them out (audit B M4)."""
    later = {"analysis": ("report",), "report": ()}.get(name, ("analysis", "report"))
    return sum(budget.cap_for(caps, s, n, u) for s in later)


def cmd_registered(args: argparse.Namespace) -> int:
    """One registered stage by name, with everything else from the frozen plan and the frozen cap table. The only free arguments are the run directory and the freeze commit."""
    name = args.name
    repo = core.ROOT
    run_dir = Path(args.run_dir).resolve()
    ledger = Ledger()
    try:
        if name not in REGISTERED_STAGES:
            raise StageRefused(f"unknown registered stage {name!r}; the stages are {', '.join(REGISTERED_STAGES)}")
        if args.caps != str(core.CAPS_FILE):
            raise StageRefused(f"refused: --caps must be {core.CAPS_FILE}: a typed cap table replaces nothing")
        check_code_location(repo)
        ident = freeze.check_preconditions(repo, args.freeze_commit)
        freeze.check_freeze_identity(repo, ident["commit"])
        plan = freeze.load_plan(repo)
        freeze.verify_plan(plan, repo, run_dir, ledger=ledger)
        freeze.check_decision(repo, ident["commit"])
        caps = json.loads((repo / core.CAPS_FILE).read_text())
        n, u = int(plan["design"]["replicates"]), int(plan["design"]["updates"])
        cap_seconds = budget.cap_for(caps, name, n, u)
        require_order(run_dir, name)
        reserve = reserved_seconds(caps, name, n, u)
        ledger.refuse_if_over((cap_seconds + reserve) / 3600.0, float(plan["cap_hours"]), f"stage {name} (its cap plus the reserved analysis and report caps)")
        device_name = str(plan["design"]["device"]) if name in ("gates", "train") else str(plan["design"].get("scoring_device", "cpu"))
        try:
            train.select_device(device_name)
        except RuntimeError as e:
            raise StageRefused(f"refused: the frozen device {device_name!r} cannot be used by this process ({e}); there is no fallback") from e
    except (freeze.FreezeRefused, budget.CapMissing, LedgerRefused, budget.CapRefused, StageRefused) as e:
        say(str(e), sys.stderr)
        return 2
    prefreeze = dict(plan.get("prefreeze", {}))
    design = {"replicates": n, "updates": u}
    pre_record = json.loads((repo / plan["prefreeze_record"]["path"]).read_text())
    data_dir = repo / plan["data_dir"]
    needs_world = name in ("gates", "train", "evaluate", "timing", "recompute")
    kind = {"gates": "gates-registered", "train": "train", "evaluate": "evaluate", "timing": "timing", "recompute": "recompute", "analysis": "analysis", "report": "report"}[name]
    core.reset_seed_record()
    status, error, stopped = "completed", "", []
    t0 = time.perf_counter()
    with ledger.measure(kind, process=f"registered {name}", registered=needs_world) as rid:
        guard = StageGuard(name, cap_seconds=cap_seconds, memory_limit_bytes=int(float(core.CFG["budget"]["memory_per_worker_gib"]) * GIB))
        deadline = Deadline(cap_seconds)
        try:
            with guard:
                if needs_world:
                    run = RunConfig.registered(int(plan["design"]["layer"]), u, float(plan["design"]["store_lr"]), float(plan["design"]["lora_lr"]), device_name)
                    bundle = read_bundle(data_dir)
                    world = build_world(bundle, "registered-run", n, run)
                    manifest = manifest_gates(data_dir)
                    if file_sha256(data_dir / "manifest.json") != plan["data_manifest_sha256"]:
                        raise StageRefused("the data manifest differs from the frozen one")
                fns: dict[str, Callable[[], Any]] = {
                    "gates": lambda: stage_gates(world, run_dir, core.SeedPlan("registered-run", 0), g1=gate_inputs(world, pre_record)[0], g3=gate_inputs(world, pre_record)[1], equivalence_record=bundle.extra.get("equivalence"), file_manifest=manifest, root=data_dir, require_mps=device_name == "mps"),
                    "train": lambda: stage_train(world, run_dir, deadline),
                    "evaluate": lambda: stage_evaluate(world, run_dir, deadline),
                    "timing": lambda: stage_timing(world, run_dir, deadline=deadline),
                    "recompute": lambda: stage_recompute(world, run_dir, deadline),
                    "analysis": lambda: stage_analysis(run_dir, design, prefreeze),
                    "report": lambda: stage_report(run_dir),
                }  # fmt: skip
                result = fns[name]()
                stopped = list(result.get("stopped", [])) if isinstance(result, dict) else []
                if stopped:
                    status = "stopped"
                if needs_world:
                    _write_seed_record(run_dir, name, n)
        except (CapReached, MemoryLimitExceeded) as e:
            status, error = "stopped", str(e)
            stopped = [*stopped, str(e)]
        except Exception as e:  # noqa: BLE001
            status, error = "failed", f"{type(e).__name__}: {e}"
        mem = guard.record()
    record(run_dir / "memory" / f"{name}.json", mem)
    record(stage_record_path(run_dir, name), {"stage": name, "status": status, "error": error, "stopped": stopped, "seconds": time.perf_counter() - t0, "run_id": rid, "memory_exceeded": mem["memory_exceeded"], "at": _utc(), "design": design, "device": device_name, "scoring_environment": {"threads": int(core.CFG["budget"]["timing_threads"]), "deterministic_algorithms": True}})
    if status == "failed":
        say(f"stage {name} failed: {error}", sys.stderr)
        return 1
    if status == "stopped":
        say(f"stage {name} stopped (the label will be INCOMPLETE): {error or '; '.join(stopped)}")
    return 0


def _write_seed_record(run_dir: Path, name: str, n: int) -> None:
    """The seeds actually used by this registered process, with the G9 reading (audit B m7: nothing wrote the seed record of the train and evaluate processes). The gates stage's own record is inside
    ``gates.json``; this file is written for every world-building stage. A seed outside the planned set, or a label other than ``registered-run``, fails the stage."""
    recs = core.seed_record()
    planned = gates.planned_all("registered-run", n)
    gate = core.seed_gate(recs, planned, planned_mode="registered-run", extra_foreign=core.config_seeds())
    problems = list(gate["problems"])
    for u in recs:
        if u.mode != "registered-run" or u.seed not in planned:
            problems.append(f"{u.seed} ({u.purpose}) mode {u.mode!r}: not a planned registered-run seed")
    record(run_dir / "seeds" / f"{name}.json", {"stage": name, "ok": not problems, "problems": problems, "recorded": gate["recorded"], "planned": planned})
    if problems:
        raise RuntimeError("G9: " + "; ".join(problems[:4]))


# --- pre-freeze commands -------------------------------------------------------------------------------------------------------------------------
def _prefreeze_start(args: argparse.Namespace, ledger: Ledger, what: str, outputs: Sequence[str]) -> Path | None:
    """The shared start of a pre-freeze stage: a clean HEAD, the stage cap against the study ledger's room, write-once outputs. Returns the run directory, or None after printing the refusal."""
    try:
        freeze.check_code_commit(core.ROOT, args.code_commit)
        run_dir = Path(args.run_dir).resolve()
        for o in outputs:
            if (run_dir / o).exists():
                raise StageRefused(f"refused: {run_dir / o} exists: {what} is run once and its record is write-once")
        ledger.refuse_if_over(float(args.stage_cap_seconds) / 3600.0, None, what)
        return run_dir
    except (freeze.FreezeRefused, LedgerRefused, StageRefused) as e:
        say(str(e), sys.stderr)
        return None


def _device(args: argparse.Namespace) -> str:
    return str(args.device) if args.device else str(core.CFG["budget"]["training_device"])


def cmd_calibrate(args: argparse.Namespace) -> int:
    """Calibration and the pilot gate (section 12.1, 12.2) on the frozen data files and calibration seeds."""
    from . import calibration

    ledger = Ledger()
    run_dir = _prefreeze_start(args, ledger, "calibration", ["calibration.json", "calibration_stopped.json"])
    if run_dir is None:
        return 2
    updates = int(args.updates) if args.updates else int(core.CFG["calibration"]["updates"])
    try:
        train.select_device(_device(args))
    except RuntimeError as e:
        say(f"refused: the device {_device(args)!r} cannot be used ({e}); there is no fallback", sys.stderr)
        return 2
    core.reset_seed_record()
    code = 0
    with ledger.measure("calibration", process="calibration and pilot"):
        try:
            with StageGuard("calibration", cap_seconds=float(args.stage_cap_seconds)):
                world = build_world(read_bundle(Path(args.data_dir)), "calibration", 1, RunConfig.registered(core.READ_LAYERS[0], updates, core.CFG["training"]["store_learning_rate"], core.CFG["training"]["lora_learning_rates"][0], _device(args)))
                rec = calibration.run_calibration(world, 0, updates=updates)
        except (CapReached, MemoryLimitExceeded, calibration.CalibrationFailed) as e:
            record(run_dir / "calibration_stopped.json", {"stopped": str(e), "at": _utc()})
            say(f"calibration stopped: {e}", sys.stderr)
            code = 4
    if code:
        return code
    record(run_dir / "calibration.json", rec)
    say(f"calibration record written to {run_dir / 'calibration.json'}")
    return 0 if rec["pilot"]["ok"] else 3


def _read_calibration(run_dir: Path) -> dict[str, Any]:
    p = run_dir / "calibration.json"
    if not p.is_file():
        raise StageRefused(f"refused: {p} does not exist: the layer and the learning rates come from the calibration record")
    return dict(read_json(p))


def cmd_prefreeze_gates(args: argparse.Namespace) -> int:
    """The gates stage at real size on rehearsal seeds before the freeze (section 12.3), on the rehearsal world: calibration items stand in for every evaluation panel (the lead's ruling A-M3). Its scaled time
    becomes the second gates stage's time in R."""
    from . import rehearsal

    ledger = Ledger()
    run_dir = _prefreeze_start(args, ledger, "the pre-freeze gates stage", ["prefreeze_gates.json"])
    if run_dir is None:
        return 2
    try:
        cal = _read_calibration(run_dir)
        train.select_device(_device(args))
    except (StageRefused, RuntimeError) as e:
        say(str(e), sys.stderr)
        return 2
    layer = int(cal["selection"]["read_layer"])
    n = max(a for a, _b in budget.rungs())
    core.reset_seed_record()
    data_dir = Path(args.data_dir)
    pre = json.loads((run_dir / "data" / "prefreeze_record.json").read_text())
    with ledger.measure("gates-rehearsal", process="pre-freeze gates on rehearsal seeds"):
        with StageGuard("prefreeze-gates", cap_seconds=float(args.stage_cap_seconds)):
            bundle = read_bundle(data_dir)
            world = build_world(bundle, "rehearsal", n, RunConfig.registered(layer, int(core.CFG["rehearsal"]["short_updates"]), core.CFG["training"]["store_learning_rate"], float(cal["selection"]["lora_lr"]), _device(args)))
            g1, g3 = gate_inputs(world, pre)
            with scoring_environment():
                rec = rehearsal.time_prefreeze_gates(world, run_dir, g1, g3, bundle.extra.get("equivalence"), manifest_gates(data_dir), data_dir, require_mps=_device(args) == "mps")
    record(run_dir / "prefreeze_gates.json", rec)
    say(f"pre-freeze gates record written to {run_dir / 'prefreeze_gates.json'}: ok = {rec['ok']}")
    return 0 if rec["ok"] else 3


def cmd_rehearse(args: argparse.Namespace) -> int:
    """The rehearsal (section 13.3): the rates measured by the registered stage functions, the headroom check and the rung rule's decision."""
    from . import rehearsal

    ledger = Ledger()
    run_dir = _prefreeze_start(args, ledger, "the rehearsal", ["rates.json", "rehearsal.json"])
    if run_dir is None:
        return 2
    try:
        cal = _read_calibration(run_dir)
        if not cal["pilot"]["ok"]:
            raise StageRefused(f"{cal['pilot'].get('outcome')}: the rehearsal does not run (section 12.2)")
        pg_path = run_dir / "prefreeze_gates.json"
        if not pg_path.is_file():
            raise StageRefused(f"refused: {pg_path} does not exist: the pre-freeze gates stage on rehearsal seeds runs before the rehearsal and its time is the second gates stage's")
        pg = read_json(pg_path)
        if not pg.get("ok"):
            raise StageRefused("refused: the pre-freeze gates stage failed (a failed gate stops the run)")
        dev = _device(args)
        if dev != "mps" and not args.device_reason:
            raise StageRefused(f"refused: the training device is {dev!r}: a non-MPS rehearsal needs --device-reason (the ADR's rule: unsupported MPS operations move training to CPU, recorded before the freeze)")
        train.select_device(dev)
    except (StageRefused, RuntimeError) as e:
        say(str(e), sys.stderr)
        return 2
    layer, lora_lr = int(cal["selection"]["read_layer"]), float(cal["selection"]["lora_lr"])
    short = int(args.updates) if args.updates else int(core.CFG["rehearsal"]["short_updates"])
    full = int(args.full_updates) if args.full_updates else int(core.CFG["rehearsal"]["full_updates"])
    core.reset_seed_record()
    data_dir = Path(args.data_dir)
    scratch = run_dir / "rehearsal-scratch"
    with ledger.measure("rehearsal", process="rehearsal"):
        with StageGuard("rehearsal", cap_seconds=float(args.stage_cap_seconds)):
            overhead = rehearsal.measure_task_overhead(data_dir, core.ROOT, layer=layer, lora_lr=lora_lr)
            world = build_world(read_bundle(data_dir), "rehearsal", 1, RunConfig.registered(layer, short, core.CFG["training"]["store_learning_rate"], lora_lr, dev))
            rates, raw = rehearsal.measure_rates(world, 0, updates=short, full_updates=full, overhead=overhead, gates2_seconds=float(pg["seconds_scaled_to_registered_panels"]), scratch=scratch, data_dir=data_dir, repo=core.ROOT, device_reason=str(args.device_reason or ""))
    record(run_dir / "rates.json", rates.to_json())
    p_hours = ledger.total_hours()
    check = budget.headroom_check(p_hours, rates, ledger, core.ROOT / core.RAISE_FILE)
    record(run_dir / "rehearsal.json", {"raw": raw, "charged_hours_at_end_of_rehearsal": p_hours, "headroom_check": check, "memory_check": budget.memory_check(rates)})
    say(f"rehearsal record written to {run_dir / 'rehearsal.json'}; rung rule outcome: {check['decision']['outcome']}")
    return 0


def cmd_raise_cap(args: argparse.Namespace) -> int:
    """Record the cap raise (the lead's act at the headroom check): the amount is recomputed from the rehearsal record and the study ledger, never typed; refused after any registered seed."""
    try:
        rates = budget.Rates.from_json(read_json(Path(args.run_dir) / "rates.json"))
        rec = budget.record_raise(rates, core.ROOT / core.RAISE_FILE, Ledger(), repo=core.ROOT)
    except (budget.CapRefused, FileNotFoundError) as e:
        say(str(e), sys.stderr)
        return 2
    say(f"cap raised from {rec['old_cap_hours']} h to {rec['new_cap_hours']} h (recomputed from the rehearsal record; recorded in {core.RAISE_FILE} and in the study ledger)")
    return 0


def cmd_freeze(args: argparse.Namespace) -> int:
    repo = core.ROOT
    pre = Path(args.pre_run_dir)
    ledger = Ledger()
    try:
        rates = budget.Rates.from_json(read_json(pre / "rates.json"))
        rec = freeze.write_freeze(repo, rates=rates, ledger=ledger, run_dir=Path(args.run_dir), data_dir=args.data_dir, calibration=pre / "calibration.json", prefreeze=pre / "data" / "prefreeze_record.json", prefreeze_gates=pre / "prefreeze_gates.json", rehearsal=pre / "rehearsal.json")
    except (freeze.FreezeRefused, budget.CapRefused, FileNotFoundError) as e:
        say(str(e), sys.stderr)
        return 2
    say(f"freeze files written: {', '.join(rec['written'])}")
    return 0


def cmd_dry(args: argparse.Namespace) -> int:
    out = dry(Path(args.run_dir), replicates=args.replicates, updates=args.updates)
    output.emit_plain(f"dry stage complete: gates ok = {out['gates']['ok']}; outputs in {args.run_dir}")
    return 0 if out["gates"]["ok"] else 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m studies.p10s2.stages", description="P10S2 stage drivers (ADR-0022 revision 5). Implementation on synthetic stand-ins only.")
    sub = p.add_subparsers(dest="command", required=True)
    d = sub.add_parser("dry", help="tiny synthetic end-to-end (stand-ins, test seeds; not a calibration, rehearsal or registered stage)")
    d.add_argument("--run-dir", required=True)
    d.add_argument("--replicates", type=int, default=2)
    d.add_argument("--updates", type=int, default=None)
    d.set_defaults(func=cmd_dry)
    r = sub.add_parser("registered", help="one registered stage by name, from the frozen plan (no other argument exists)")
    r.add_argument("name", choices=REGISTERED_STAGES)
    r.add_argument("--run-dir", required=True)
    r.add_argument("--freeze-commit", required=True)
    r.add_argument("--caps", required=True, choices=[str(core.CAPS_FILE)], help="the frozen stage-cap table (every launch script passes it); no other path is accepted")
    r.set_defaults(func=cmd_registered)
    for name, fn, hlp in (
        ("calibrate", cmd_calibrate, "calibration and the pilot gate on calibration seeds (pre-freeze)"),
        ("prefreeze-gates", cmd_prefreeze_gates, "the gates stage at real size on rehearsal seeds, on calibration items (pre-freeze; its time is the second gates stage's)"),
        ("rehearse", cmd_rehearse, "the rehearsal: rates, headroom check, rung rule (pre-freeze)"),
    ):
        c = sub.add_parser(name, help=hlp)
        c.add_argument("--run-dir", required=True)
        c.add_argument("--code-commit", required=True, help="must equal a clean HEAD")
        c.add_argument("--stage-cap-seconds", type=float, required=True, help="the stage cap (seconds); every launch script passes it; it is enforced as a deadline and checked against the study ledger's room")
        c.add_argument("--data-dir", required=True)
        c.add_argument("--updates", type=int, default=None, help="default: from the configuration")
        if name == "rehearse":
            c.add_argument("--full-updates", type=int, default=None, help="default: from the configuration ([rehearsal] full_updates)")
            c.add_argument("--device-reason", default=None, help="required if the training device is not MPS")
        c.add_argument("--device", default=None, choices=["mps", "cpu"], help="default: the configured training device (MPS); there is no automatic choice")
        c.set_defaults(func=fn)
    rc = sub.add_parser("raise-cap", help="record the cap raise at the rehearsal's headroom check; the amount is recomputed from the rehearsal record and the study ledger")
    rc.add_argument("--run-dir", required=True, help="the pre-freeze run directory (holds rates.json)")
    rc.set_defaults(func=cmd_raise_cap)
    f = sub.add_parser("freeze", help="write the frozen plan and cap files from the pre-freeze records (the freeze procedure)")
    f.add_argument("--pre-run-dir", required=True, help="the pre-freeze run directory: rates.json, calibration.json, prefreeze_gates.json, rehearsal.json, data/prefreeze_record.json")
    f.add_argument("--run-dir", required=True, help="the registered run directory the plan binds")
    f.add_argument("--data-dir", required=True, help="the data bundle, relative to the repository")
    f.set_defaults(func=cmd_freeze)
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    code = args.func(args)
    return int(code)


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["main", "dry", "build_parser", "DataBundle", "registry"]
