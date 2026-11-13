"""Prespecified untimed operand probes and isolated latency measurements."""

from __future__ import annotations

import gc
import math
import statistics
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from functools import partial
from typing import Any

import torch
from torch import Tensor
from torch.utils._python_dispatch import TorchDispatchMode

from .p5_config import BASELINE, DENSE, FLAT, MEMORIES, VARIANTS, rotate
from .p5_model import Model, insertion_hidden, normalized_query
from .pilot_model import Memory

LOOKUP, ADDITION, FORWARD = "lookup_score_select", "addition_forward", "model_forward"
SCOPES = (LOOKUP, ADDITION, FORWARD)
WORKLOADS = (8, 1)
ROUNDS, WARMUPS, CALLS = 8, 2, 10


@dataclass(frozen=True)
class Block:
    batch_size: int
    scope: str
    round: int
    variant: str
    warm: tuple[int, ...]
    timed: tuple[int, ...]


def schedule(index: int, variants: tuple[str, ...]) -> Iterable[Block]:
    if variants not in (VARIANTS, (BASELINE,)) or not 0 <= index < 27:
        raise ValueError("unregistered P5 timing group")
    for size in WORKLOADS:
        for scope in SCOPES:
            valid = tuple(
                v
                for v in variants
                if scope == FORWARD or (v in MEMORIES or (scope == ADDITION and v == DENSE))
            )
            if not valid:
                continue
            for round_id in range(ROUNDS):
                for variant in rotate(valid, index + round_id):
                    yield Block(
                        size,
                        scope,
                        round_id,
                        variant,
                        tuple((round_id * WARMUPS + j) % 4 for j in range(WARMUPS)),
                        tuple((round_id * CALLS + j) % 4 for j in range(CALLS)),
                    )


def summarize(rounds: list[list[int]], resolution_ns: float) -> dict[str, Any]:
    if len(rounds) != ROUNDS or any(len(row) != CALLS for row in rounds):
        raise ValueError("wrong P5 timing repetition count")
    durations = [value for row in rounds for value in row]
    if not math.isfinite(resolution_ns) or resolution_ns <= 0:
        raise ValueError("invalid timing resolution")
    medians = [statistics.median(row) for row in rounds]
    ratio = max(medians) / min(medians) if min(medians) > 0 else None
    median = statistics.median(durations)
    ordered = sorted(durations)
    criteria = {
        "positive_durations": min(durations) > 0,
        "above_clock_resolution": median >= 100 * resolution_ns,
        "stable_rounds": ratio is not None and ratio <= 1.25,
    }
    return {
        "durations_ns": durations,
        "round_medians_ns": medians,
        "median_ns": median,
        **{
            f"p{int(p * 100)}_ns": ordered[math.ceil(len(ordered) * p) - 1]
            for p in (0.1, 0.9, 0.95)
        },
        "min_ns": min(durations),
        "max_ns": max(durations),
        "round_median_ratio": ratio,
        "resolution_ns": resolution_ns,
        "reliability_criteria": criteria,
        "usable": all(criteria.values()),
    }


def inputs_from_rows(rows: Tensor) -> dict[int, tuple[Tensor, ...]]:
    if rows.ndim != 2 or rows.shape[0] < 32 or rows.shape[1] != 65:
        raise ValueError("P5 timing requires the registered ranked inputs")
    return {
        size: tuple(rows[start : start + size, :64].contiguous() for start in (0, 8, 16, 24))
        for size in WORKLOADS
    }


def run_schedule(
    models: dict[str, Model],
    inputs: dict[int, tuple[Tensor, ...]],
    index: int,
    *,
    clock: Callable[[], int] = time.perf_counter_ns,
    on_block: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    from .longer_training import _isolated_rng

    variants = tuple(models)
    blocks = list(schedule(index, variants))
    counters = {"insertion_hidden": 0, "normalized_query": 0, "warmups": 0, "timed": 0}
    grouped: dict[tuple[int, str, str], list[list[int]]] = {}
    features: dict[tuple[int, str, str], list[Callable[[], object]]] = {}
    original_modes = {variant: model.training for variant, model in models.items()}
    clock_info = time.get_clock_info("perf_counter")
    resolution = clock_info.resolution * 1e9
    try:
        with _isolated_rng(), torch.inference_mode():
            for variant, model in models.items():
                model.eval()
                for size, batches in inputs.items():
                    features[size, FORWARD, variant] = [partial(model, x) for x in batches]
                    addition = model.addition
                    if addition is not None:
                        hs = [insertion_hidden(model, x) for x in batches]
                        counters["insertion_hidden"] += len(hs)
                        features[size, ADDITION, variant] = [partial(addition, h) for h in hs]
                        if isinstance(addition, Memory):
                            qs = [normalized_query(addition, h) for h in hs]
                            counters["normalized_query"] += len(qs)
                            features[size, LOOKUP, variant] = [
                                partial(addition.lookup, q) for q in qs
                            ]
            for block in blocks:
                key = (block.batch_size, block.scope, block.variant)
                calls = features[key]
                gc_was_enabled = gc.isenabled()
                durations = []
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
                if on_block is not None:
                    on_block(
                        {
                            "batch_size": block.batch_size,
                            "scope": block.scope,
                            "variant": block.variant,
                            "round": block.round,
                            "warmup_input_indexes": list(block.warm),
                            "timed_input_indexes": list(block.timed),
                            "durations_ns": durations,
                        }
                    )
    finally:
        for variant, model in models.items():
            model.train(original_modes[variant])
    return {
        "records": [
            {"batch_size": size, "scope": scope, "variant": variant, **summarize(rows, resolution)}
            for (size, scope, variant), rows in grouped.items()
        ],
        "call_counts": counters,
        "clock": {
            "implementation": clock_info.implementation,
            "resolution_ns": resolution,
            "monotonic": clock_info.monotonic,
            "adjustable": clock_info.adjustable,
        },
    }


def _describe(value: Any) -> Any:
    if isinstance(value, Tensor):
        return {"shape": list(value.shape), "dtype": str(value.dtype), "elements": value.numel()}
    if isinstance(value, list | tuple):
        return [_describe(x) for x in value]
    if isinstance(value, int | float | str | bool) or value is None:
        return value
    return str(value)


class OperandTrace(TorchDispatchMode):
    """Record actual operator operands/results; never active during timed calls."""

    def __init__(self) -> None:
        super().__init__()  # type: ignore[no-untyped-call]
        self.events: list[dict[str, Any]] = []

    def __torch_dispatch__(
        self,
        func: Any,
        types: Any,
        args: Any = (),
        kwargs: Any = None,
    ) -> Any:
        options = kwargs or {}
        result = func(*args, **options)
        self.events.append(
            {
                "operator": str(func),
                "args": _describe(args),
                "kwargs": {key: _describe(value) for key, value in options.items()},
                "result": _describe(result),
            }
        )
        return result


def _one(
    events: list[dict[str, Any]], op: str | tuple[str, ...], shape: list[int]
) -> dict[str, Any]:
    names = (op,) if isinstance(op, str) else op
    found = [row for row in events if row["operator"] in names and row["args"][0]["shape"] == shape]
    if len(found) != 1:
        raise ValueError(f"P5 wrong observed operation count for {op} {shape}: {len(found)}")
    return found[0]


def trace_memory(model: Model, tokens: Tensor) -> dict[str, Any]:
    from .longer_training import _isolated_rng

    memory = model.addition
    if not isinstance(memory, Memory):
        raise ValueError("P5 work trace requires a memory model")
    with _isolated_rng(), torch.inference_mode():
        h = insertion_hidden(model, tokens)
        trace = OperandTrace()
        with trace:
            _, lookup = memory(h)
    n = tokens.numel()
    variant = model.cell.variant
    events = trace.events
    if list(lookup.selected.shape) != [n, 8] or not bool(
        ((lookup.selected >= 0) & (lookup.selected < 4096)).all()
    ):
        raise ValueError("P5 wrong traced selected value count/IDs")
    top8 = [
        e
        for e in events
        if e["operator"] == "aten.gather.default"
        and e["args"][0]["shape"] == [n, 4096 if variant == FLAT else 512]
        and e["result"]["shape"] == [n, 8]
    ]
    if len(top8) < 1 or not any("topk" in e["operator"] for e in events):
        raise ValueError("P5 score selection operations missing from trace")
    values = _one(events, "aten.index.Tensor", [4096, 32])
    if values["args"][1][0]["shape"] != [n, 8] or values["result"]["shape"] != [n, 8, 32]:
        raise ValueError("P5 selected value gather shape mismatch")
    if variant == FLAT:
        score = _one(events, ("aten.mm.default", "aten.matmul.default"), [n, 16])
        if (
            score["args"][1]["shape"] != [16, 4096]
            or score["result"]["shape"] != [n, 4096]
            or lookup.candidate_ids is not None
            or lookup.branch_ids is not None
        ):
            raise ValueError("P5 flat score/lookup mismatch")
        key_norm = _one(events, "aten.linalg_vector_norm.default", [4096, 16])
        router, router_elements, router_norm_elements = 0, 0, 0
        candidate_union = 4096
    else:
        route = _one(events, ("aten.mm.default", "aten.matmul.default"), [n, 16])
        score = _one(events, "aten.bmm.default", [n, 512, 16])
        router_norm = _one(events, "aten.linalg_vector_norm.default", [16, 16])
        key_norm = _one(events, "aten.linalg_vector_norm.default", [n, 512, 16])
        gather = _one(events, "aten.index.Tensor", [4096, 16])
        candidates, branches = lookup.candidate_ids, lookup.branch_ids
        if (
            route["args"][1]["shape"] != [16, 16]
            or route["result"]["shape"] != [n, 16]
            or score["args"][1]["shape"] != [n, 16, 1]
            or score["result"]["shape"] != [n, 512, 1]
            or gather["args"][1][0]["shape"] != [n, 512]
            or gather["result"]["shape"] != [n, 512, 16]
            or candidates is None
            or list(candidates.shape) != [n, 512]
            or branches is None
            or list(branches.shape) != [n, 2]
            or not bool((lookup.selected[:, :, None] == candidates[:, None, :]).any(-1).all())
        ):
            raise ValueError("P5 tree score/gather/lookup mismatch")
        router = route["result"]["shape"][-1]
        router_elements = route["args"][1]["elements"]
        router_norm_elements = router_norm["args"][0]["elements"]
        candidate_union = candidates.unique().numel()
    dots = score["result"]["shape"][-1 if variant == FLAT else -2]
    return {
        "variant": variant,
        "queries": n,
        "key_dot_products_per_query": dots,
        "router_dot_products_per_query": router,
        "candidate_key_elements_per_query": dots * 16,
        "router_elements_per_query": router_elements,
        "selected_values_per_query": values["result"]["shape"][1],
        "key_normalization_input_elements": key_norm["args"][0]["elements"],
        "router_normalization_input_elements": router_norm_elements,
        "candidate_union": candidate_union,
        "selected_union": lookup.selected.unique().numel(),
        "operators": events,
        "validated": True,
    }
