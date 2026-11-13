"""P6-E timing stages T-screen and T-confirm (ADR-0011 sections 3.4 and 3.5).

The protocol of ADR-0010 section 7 is reused unchanged: inputs from ranked training chunks 0-31,
three scopes with P5's boundaries, ``perf_counter_ns``, GC disabled only inside timing blocks,
no outlier deletion, no adaptive repetition, no best-time selection, 8 rounds of 2 untimed
warmups plus 10 timed calls, variant order rotated by ``(i + round) mod n`` and the reliability
rule of ``p5_timing.summarize``. Raw nanosecond samples are retained.

Nothing in this module executes the registered study when imported. Status: SPEC:
HUMAN-APPROVED (ADR-0011); implementation self-checked only.
"""

import gc
import random
import sys
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Any

import torch
from torch import Tensor

from .io import canonical_json, file_sha256, read_json, sha256, write_json
from .p5_config import rotate
from .p5_model import insertion_hidden, normalized_query
from .p5_timing import inputs_from_rows
from .p6_analysis import (
    ADDITION,
    CALLS,
    FORWARD,
    LOOKUP,
    ROUNDS,
    WARMUPS,
    confirm_entities,
    eligibility_from_gate,
    select_variants,
    summarize_rounds,
)
from .p6_common import KNOWN_LIMITS, StudyArgs, compact_evidence, load_cell, pair_index
from .p6_retrieval import FastMemory, build_variant_model
from .p6_stage import (
    StageContext,
    finish_stage,
    open_stage,
    require_completed,
    run_worker_stage,
    source_expectations,
    verify_source_unchanged,
)
from .pilot_model import Memory
from .records import append_event

WORKLOADS = ("W8", "W1", "Wtok")
SHAPES = {"W8": (8, 64), "W1": (1, 64), "Wtok": (1, 1)}  # batch size, context length
REFERENCE = {"flat": "F0", "fixed_tree": "T0", "learned_tree": "T0"}
CANONICAL = ("flat", "fixed_tree", "learned_tree")


def scopes_for(workload: str) -> tuple[str, ...]:
    """Wtok is descriptive: lookup and addition scopes only."""
    return (LOOKUP, ADDITION) if workload == "Wtok" else (LOOKUP, ADDITION, FORWARD)


@dataclass(frozen=True)
class Block:
    workload: str
    scope: str
    round: int
    entity: str
    warm: tuple[int, ...]
    timed: tuple[int, ...]


def schedule(index: int, entities: tuple[str, ...], *, rounds: int = ROUNDS) -> Iterable[Block]:
    """P5's schedule over P6 entities: rotation by (index + round) within every scope."""
    if not 0 <= index < 27 or not entities or len(set(entities)) != len(entities):
        raise ValueError("invalid P6 timing group")
    for workload in WORKLOADS:
        for scope in scopes_for(workload):
            for round_id in range(rounds):
                for name in rotate(entities, index + round_id):
                    yield Block(
                        workload,
                        scope,
                        round_id,
                        name,
                        tuple((round_id * WARMUPS + j) % 4 for j in range(WARMUPS)),
                        tuple((round_id * CALLS + j) % 4 for j in range(CALLS)),
                    )


def expected_scope_calls(entity_count: int, rounds: int = ROUNDS) -> int:
    scopes = sum(len(scopes_for(w)) for w in WORKLOADS)
    return scopes * rounds * entity_count * (WARMUPS + CALLS)


def workload_inputs(train: Tensor) -> dict[str, tuple[Tensor, ...]]:
    """W8 and W1 exactly as P5; Wtok is the first token of each W1 input."""
    registered = inputs_from_rows(train)
    return {
        "W8": registered[8],
        "W1": registered[1],
        "Wtok": tuple(x[:, :1].contiguous() for x in registered[1]),
    }


def source_memory(model: Any) -> Memory:
    memory = model.addition
    return memory.source if isinstance(memory, FastMemory) else memory


def run_timing(
    entities: dict[str, Any],
    inputs: dict[str, tuple[Tensor, ...]],
    index: int,
    *,
    rounds: int = ROUNDS,
    clock: Callable[[], int] = time.perf_counter_ns,
    on_block: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    from .longer_training import _isolated_rng

    names = tuple(entities)
    blocks = list(schedule(index, names, rounds=rounds))
    counters = {"insertion_hidden": 0, "normalized_query": 0, "warmups": 0, "timed": 0}
    grouped: dict[tuple[str, str, str], list[list[int]]] = {}
    fallbacks: dict[tuple[str, str, str], list[list[int]]] = {}
    features: dict[tuple[str, str, str], list[Callable[[], object]]] = {}
    clock_info = time.get_clock_info("perf_counter")
    resolution = clock_info.resolution * 1e9
    with _isolated_rng(), torch.inference_mode():
        for name, model in entities.items():
            for workload, batches in inputs.items():
                if workload != "Wtok":
                    features[workload, FORWARD, name] = [partial(model, x) for x in batches]
                hs = [insertion_hidden(model, x) for x in batches]
                counters["insertion_hidden"] += len(hs)
                features[workload, ADDITION, name] = [partial(model.addition, h) for h in hs]
                qs = [normalized_query(source_memory(model), h) for h in hs]
                counters["normalized_query"] += len(qs)
                features[workload, LOOKUP, name] = [partial(model.addition.lookup, q) for q in qs]
        for block in blocks:
            key = (block.workload, block.scope, block.entity)
            calls = features[key]
            log = getattr(entities[block.entity].addition, "fallback_log", None)
            logged = len(log) if log is not None else 0
            gc_was_enabled = gc.isenabled()
            durations: list[int] = []
            try:
                gc.disable()
                for sample in block.warm:
                    calls[sample]()
                for sample in block.timed:
                    function = calls[sample]
                    start = clock()
                    function()
                    durations.append(clock() - start)
            finally:
                if gc_was_enabled:
                    gc.enable()
                else:
                    gc.disable()
            counters["warmups"] += len(block.warm)
            counters["timed"] += len(block.timed)
            grouped.setdefault(key, []).append(durations)
            if log is not None and len(log) > logged:
                added = log[logged:]
                if len(added) != len(block.warm) + len(block.timed):
                    raise ValueError("P6 stop: guard fallback log does not match the call count")
                fallbacks.setdefault(key, []).extend([list(x) for x in added[len(block.warm) :]])
            if on_block is not None:
                on_block(
                    {
                        "workload": block.workload,
                        "scope": block.scope,
                        "entity": block.entity,
                        "round": block.round,
                        "warmup_input_indexes": list(block.warm),
                        "timed_input_indexes": list(block.timed),
                        "durations_ns": durations,
                        "guard_fallback_timed_calls": fallbacks.get(key, [])[-len(block.timed) :],
                    }
                )
    return {
        "records": [
            {
                "workload": workload,
                "scope": scope,
                "entity": name,
                "kind": name.split(":")[0],
                "variant": name.split(":")[1],
                **summarize_rounds(rows, resolution, expected_rounds=rounds),
                **_fallback_fields(fallbacks.get((workload, scope, name))),
            }
            for (workload, scope, name), rows in grouped.items()
        ],
        "call_counts": counters,
        "clock": {
            "implementation": clock_info.implementation,
            "resolution_ns": resolution,
            "monotonic": clock_info.monotonic,
            "adjustable": clock_info.adjustable,
        },
    }


def _fallback_fields(calls: list[list[int]] | None) -> dict[str, Any]:
    """Guard-band fallback per timed call: [queries, flagged queries], in timed-call order."""
    if calls is None:
        return {}
    queries = sum(n for n, _ in calls)
    flagged = sum(f for _, f in calls)
    return {
        "guard_fallback_per_timed_call": calls,
        "guard_fallback_fraction": flagged / queries if queries else None,
    }


# ---------------------------------------------------------------------------------------------
# Allocation profile (separate, untimed pass)
# ---------------------------------------------------------------------------------------------
def allocation_profile(call: Callable[[], object]) -> dict[str, Any]:
    """Bytes allocated and peak live bytes for one call, from PyTorch's CPU memory profiler.

    Allocator-level measurement derived from profiler events (self CPU memory usage ordered by
    start time); coarse and profiler-dependent. The profiler runs only in this untimed pass.
    """
    from torch.profiler import ProfilerActivity, profile

    call()  # warm
    with profile(activities=[ProfilerActivity.CPU], profile_memory=True) as profiler:
        call()
    live = peak = allocated = 0
    events = sorted(profiler.events(), key=lambda e: e.time_range.start)
    for event in events:
        delta = int(event.self_cpu_memory_usage)
        if delta > 0:
            allocated += delta
        live += delta
        peak = max(peak, live)
    return {
        "allocated_bytes_per_call": allocated,
        "peak_live_bytes_per_call": peak,
        "net_live_bytes_after_call": live,
        "profiler_events": len(events),
        "method": "torch.profiler CPU profile_memory=True; sum of positive self_cpu_memory_usage "
        "and running-sum peak over events ordered by start time; allocator-level, approximate",
    }


# ---------------------------------------------------------------------------------------------
# Worker
# ---------------------------------------------------------------------------------------------
def _rss() -> int:
    import psutil

    return int(psutil.Process().memory_info().rss)


def canonical_entities(plan: dict[str, list[str]]) -> list[str]:
    return [f"{kind}:{variant}" for kind in CANONICAL for variant in plan.get(kind, [])]


def timing_worker(spec: dict[str, Any], child: Path, pair: tuple[int, int, int]) -> None:
    from .engine import configure_cpu

    args = StudyArgs.from_json(spec["args"])
    plan: dict[str, list[str]] = spec["plan"]
    rounds = int(args.rounds)
    configure_cpu()
    rss = {"before_load": _rss()}
    source = load_cell(args, pair, child)
    rss["after_load"] = _rss()
    for model in source.models.values():
        model.eval()
    digests = source.digests()
    python_rng, torch_rng, gc_before = random.getstate(), torch.get_rng_state(), gc.isenabled()
    modes = {kind: m.training for kind, m in source.models.items()}
    files_before = source.files_unchanged()
    # Integrity replay (ADR-0011 section 2) in this process, before any P6 measurement and outside
    # every timed region: each restored unmodified model must reproduce its recorded P5 NLL
    # bitwise, or the worker stops (integrity_replay raises on a mismatch).
    from .p6_equivalence import integrity_replay

    replay = {kind: integrity_replay(source, kind) for kind in source.models}

    entities: dict[str, Any] = {}
    construction_ns: dict[str, int] = {}
    binding_ns: dict[str, int] = {}
    extra_bytes: dict[str, int] = {}
    for name in canonical_entities(plan):
        kind, variant = name.split(":")
        model = source.models[kind]
        if variant == REFERENCE[kind]:
            entities[name] = model
            construction_ns[name], binding_ns[name], extra_bytes[name] = 0, 0, 0
            continue
        # Per-call binding check is the O(1) fingerprint in timed runs; the full hash is verified
        # before and after the timing schedule.
        built = build_variant_model(model, variant, binding="fingerprint")
        construction_ns[name] = built.addition.build_ns
        binding_ns[name] = built.addition.bind_ns
        extra_bytes[name] = built.addition.persistent_extra_bytes
        entities[name] = built
    rss["after_cache_construction"] = _rss()

    inputs = workload_inputs(source.train)
    input_bytes = bytes(source.train[:32, :64].to(torch.uint8).contiguous().reshape(-1).tolist())
    timing_inputs = {
        "input_ranks": list(range(32)),
        "time_steps": 64,
        "labels": False,
        "sha256": sha256(input_bytes),
        "workload_starts": [0, 8, 16, 24],
        "wtok": "first token of each W1 input",
    }
    first_call_ns: dict[str, int] = {}
    with torch.inference_mode():
        for name, model in entities.items():
            gc_state = gc.isenabled()
            try:
                gc.disable()
                start = time.perf_counter_ns()
                model(inputs["W8"][0])
                first_call_ns[name] = time.perf_counter_ns() - start
            finally:
                if gc_state:
                    gc.enable()
    for model in entities.values():
        if isinstance(model.addition, FastMemory):
            model.addition.verify_source()
            model.addition.reset_log()

    timing_start = time.monotonic()
    names = tuple(entities)
    timing = run_timing(
        entities,
        inputs,
        pair_index(pair),
        rounds=rounds,
        on_block=lambda row: append_event(child, {"event": "timing_block", **row}),
    )
    timing_seconds = time.monotonic() - timing_start
    rss["after_timing"] = _rss()

    fallback = {}
    for name, model in entities.items():
        if isinstance(model.addition, FastMemory):
            log = list(model.addition.fallback_log)
            total = sum(n for n, _ in log)
            fallback[name] = {
                "per_call": [list(item) for item in log],
                "calls": len(log),
                "queries": total,
                "fallback_queries": sum(f for _, f in log),
                "fraction": (sum(f for _, f in log) / total) if total else None,
            }
            model.addition.verify_source()
    memory_profile: dict[str, Any] = {}
    with torch.inference_mode():
        for name, model in entities.items():
            for workload in ("W8", "W1"):
                x = inputs[workload][0]
                h = insertion_hidden(model, x)
                q = normalized_query(source_memory(model), h)
                memory_profile[f"{name}/{workload}/{ADDITION}"] = allocation_profile(
                    partial(model.addition, h)
                )
                memory_profile[f"{name}/{workload}/{LOOKUP}"] = allocation_profile(
                    partial(model.addition.lookup, q)
                )

    expected_calls = expected_scope_calls(len(names), rounds)
    counts = timing["call_counts"]
    expected_records = {(b.workload, b.scope, b.entity) for b in schedule(0, names, rounds=rounds)}
    if (
        counts["warmups"] + counts["timed"] != expected_calls
        or {(r["workload"], r["scope"], r["entity"]) for r in timing["records"]} != expected_records
        or any(len(r["durations_ns"]) != rounds * CALLS for r in timing["records"])
    ):
        raise ValueError("P6 timing worker call or measurement matrix mismatch")
    if (
        source.digests() != digests
        or any(m.training != modes[k] for k, m in source.models.items())
        or random.getstate() != python_rng
        or not torch.equal(torch_rng, torch.get_rng_state())
        or gc.isenabled() != gc_before
        or not (files_before and source.files_unchanged())
    ):
        raise ValueError("P6 stop: timing changed model, RNG, mode, GC state or checkpoint files")
    source_recheck = verify_source_unchanged(child, spec["source"])
    write_json(
        child / "result.json",
        {
            "outcome": "completed",
            "pair": list(pair),
            "mode": spec["mode"],
            "dry_run": args.dry_run,
            "rounds": rounds,
            "plan": plan,
            "timing": timing,
            "timing_scope_calls": expected_calls,
            "timing_inputs": timing_inputs,
            "construction_ns": construction_ns,
            "binding_hash_ns": binding_ns,
            "construction_note": "construction_ns is the cache build only; binding_hash_ns is "
            "the one-time SHA-256 plus fingerprint of the source tensors; both descriptive",
            "persistent_extra_bytes": extra_bytes,
            "first_call_after_load_ns": first_call_ns,
            "first_call_note": "first W8 model_forward call per entity after construction, "
            "before the warmups; descriptive, process-order dependent",
            "guard_fallback": fallback,
            "memory_profile": memory_profile,
            "rss_bytes": rss,
            "rss_note": "sampled psutil RSS of the worker process at four points; coarse",
            "timing_seconds": timing_seconds,
            "checkpoint_evidence": compact_evidence(source),
            "state_and_rng_unchanged": True,
            "checkpoint_files_unchanged": True,
            "integrity_replay_before_timing": replay,
            "source_recheck_at_worker_end": source_recheck,
            "known_limits": list(KNOWN_LIMITS),
            "not_measured": "cache misses, memory bandwidth, physical I/O, energy",
        },
    )


# ---------------------------------------------------------------------------------------------
# Stage runners
# ---------------------------------------------------------------------------------------------
def _plan_for(
    mode: str, args: StudyArgs
) -> tuple[dict[str, list[str]], dict[str, Any] | None, dict[str, Any]]:
    """Entity plan, selection (confirm) and the evidence the plan was derived from."""
    eq_dir = require_completed(
        args.results_root, "equivalence", args.equivalence_run, dry_run=args.dry_run
    )
    equivalence = read_json(eq_dir / "result.json")
    eligibility = eligibility_from_gate(equivalence["gate"])
    if not eligibility["timing_stage_runs"]:
        raise ValueError(eligibility["reason"])
    evidence = {
        "equivalence_run": eq_dir.name,
        "equivalence_result_sha256": file_sha256(eq_dir / "result.json"),
        "eligibility": eligibility,
    }
    if mode == "screen":
        plan = {
            "flat": eligibility["flat_variants"],
            "fixed_tree": eligibility["tree_variants"],
            "learned_tree": eligibility["tree_variants"],
        }
        return plan, None, evidence
    screen_dir = require_completed(
        args.results_root, "screen", args.screen_run, dry_run=args.dry_run
    )
    screen_result = read_json(screen_dir / "result.json")
    if screen_result["evidence"]["equivalence_run"] != eq_dir.name:
        raise ValueError("the screening run consumed a different equivalence run")
    selection_path = screen_dir / "selection.json"
    selection = read_json(selection_path)
    evidence.update(
        screen_run=screen_dir.name,
        selection_sha256=file_sha256(selection_path),
        screen_result_sha256=file_sha256(screen_dir / "result.json"),
    )
    if evidence["selection_sha256"] != read_json(screen_dir / "result.json")["selection_sha256"]:
        raise ValueError("selection file differs from the hash recorded by the screening stage")
    return confirm_entities(selection), selection, evidence


def run_timing_stage(mode: str, args: StudyArgs, argv: list[str]) -> int:
    """T-screen (mode ``screen``) or T-confirm (mode ``confirm``)."""
    if mode not in ("screen", "confirm"):
        raise ValueError("mode must be screen or confirm")
    try:
        plan, selection, evidence = _plan_for(mode, args)
    except ValueError as exc:
        # E.g. no tree variant passed EQ: P6-E ends with the equivalence result, no timing run.
        print(canonical_json({"stage": mode, "status": "not_run", "reason": str(exc)}).decode())
        return 2
    context = open_stage(
        mode,
        output_root=args.output_root,
        results_root=args.results_root,
        argv=argv,
        arguments=args.to_json(),
        dry_run=args.dry_run,
        supersede=args.supersede,
        supersede_reason=args.supersede_reason,
    )
    spec = {
        "mode": mode,
        "args": args.to_json(),
        "plan": plan,
        "evidence": evidence,
        "source": source_expectations(context),
    }
    write_json(context.run / "stage-spec.json", spec)
    write_json(context.compact / "stage-spec.json", spec)
    entity_count = len(canonical_entities(plan))
    calls = expected_scope_calls(entity_count, args.rounds)

    def argv_for(pair: tuple[int, int, int], child: Path) -> list[str]:
        return [
            sys.executable,
            "-m",
            "arborlm.p6_retrieval_study",
            "_worker",
            str(context.run / "stage-spec.json"),
            str(child),
            *map(str, pair),
        ]

    outcome = run_worker_stage(context, args.pair_list(), argv_for=argv_for)
    workers = []
    for row in outcome.rows:
        path = context.compact / "workers" / f"{row['label']}.json"
        if row["status"] == "completed" and path.is_file():
            workers.append(read_json(path))
    result: dict[str, Any] = {
        "stage": mode,
        "plan": plan,
        "evidence": evidence,
        "entities_per_worker": entity_count,
        "scope_calls_per_worker": calls,
        "workers": outcome.rows,
        "completed_workers": len(workers),
        "peak_stage_process_tree_rss_bytes": outcome.peak_rss_bytes,
        "stage_wall_seconds": outcome.wall_seconds,
        "caps_note": "stage and worker wall-time caps and 2 GiB sampled RSS enforced by the "
        "supervisor; a breach stops the stage and preserves partial records",
    }
    status, reason = outcome.status, outcome.reason
    if mode == "screen" and status == "completed":
        if len(workers) != len(args.pair_list()):
            status, reason = "failed", "screening incomplete: selection rules not applied"
        else:
            selection = select_variants(workers, evidence["eligibility"])
            payload = canonical_json(selection)
            for directory in (context.run, context.compact):
                (directory / "selection.json").write_bytes(payload)
            result["selection_sha256"] = sha256(payload)
            result["selection"] = selection
    if mode == "confirm":
        result["selection_used"] = selection
    finish_stage(context, status, reason, result)
    _announce(context, status, reason)
    return 0 if status == "completed" else 1


def _announce(context: StageContext, status: str, reason: str | None) -> None:
    print(
        canonical_json(
            {"stage": context.stage, "run": context.run.name, "status": status, "reason": reason}
        )
        .decode()
        .strip(),
        flush=True,
    )
