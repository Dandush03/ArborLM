"""Recompute P5 slot and branch utilization from published counts; no model calls."""

import argparse
import json
import math
import statistics
from pathlib import Path

ROOT = Path("results/p5-2026-11-13")
VARIANTS = ("flat", "fixed_tree", "learned_tree")
PHASES = ("initial", "final")
QUERIES, SLOTS, BRANCHES, WIDTH, SELECTED = 32768, 4096, 16, 256, 8
ATOL = 1e-12


def read(path):
    return json.loads(path.read_bytes())


def counts(data, length, total):
    assert len(data) == length
    assert all(type(n) is int and 0 <= n <= QUERIES for n in data)
    assert sum(data) == total
    return data


def entropy(data):
    total = sum(data)
    nonzero = [n / total for n in data if n]
    return math.fsum(-p * math.log(p) for p in nonzero)


def match(observed, expected, key, errors):
    delta = abs(observed - expected)
    assert math.isfinite(observed) and delta <= ATOL, (key, observed, expected)
    errors[key] = max(errors.get(key, 0), delta)


def utilization(metric, variant, errors):
    assert metric["target_tokens"] == QUERIES
    retrieval = metric["retrieval"]
    assert retrieval["queries"] == QUERIES
    selected = counts(retrieval["selected_slot_counts"], SLOTS, QUERIES * SELECTED)
    selected_entropy = entropy(selected)
    slots = {
        "unique_selected_slots": sum(n > 0 for n in selected),
        "effective_selected_slots": math.exp(selected_entropy),
        "selected_slot_entropy_normalized": selected_entropy / math.log(SLOTS),
        "hottest_selected_slot_fraction": max(selected) / (QUERIES * SELECTED),
    }
    assert slots["unique_selected_slots"] == retrieval["unique_selected_slots"]
    for key, expected in slots.items():
        match(retrieval[key], expected, key, errors)
    router = retrieval["router"]
    if variant == "flat":
        assert router is None and retrieval["unique_candidate_slots"] == SLOTS
        return {**slots, "unique_candidate_slots": SLOTS}

    top = counts(router["top1_branch_counts"], BRANCHES, QUERIES)
    visited = counts(router["visited_branch_counts"], BRANCHES, QUERIES * 2)
    values = router["selected_value_branch_counts"]
    assert len(values) == BRANCHES and sum(values) == QUERIES * SELECTED
    assert values == [sum(selected[i : i + WIDTH]) for i in range(0, SLOTS, WIDTH)]
    assert all(a <= b and c <= b * SELECTED for a, b, c in zip(top, visited, values, strict=True))
    active = {
        "nonzero_top1_branches": sum(n > 0 for n in top),
        "normalized_top1_entropy": entropy(top) / math.log(BRANCHES),
        "hottest_top1_branch_fraction": max(top) / QUERIES,
    }
    assert active["nonzero_top1_branches"] == router["nonzero_top1_branches"]
    for key, expected in active.items():
        match(router[key], expected, key, errors)
    visits = sum(n > 0 for n in visited)
    assert retrieval["unique_candidate_slots"] == visits * WIDTH
    per_query = router["mean_normalized_query_router_entropy"]
    assert math.isfinite(per_query) and 0 <= per_query <= 1 + ATOL
    return {
        **slots,
        **active,
        "distinct_visited_branches": visits,
        "unique_candidate_slots": visits * WIDTH,
        "mean_normalized_query_router_entropy_reported": per_query,
    }


def distribution(values):
    if all(v is None for v in values):
        return None
    assert all(v is not None and math.isfinite(v) for v in values)
    return {
        "n": len(values),
        "mean": statistics.mean(values),
        "sample_sd": statistics.stdev(values),
        "min": min(values),
        "max": max(values),
    }


def summarize(rows):
    return {key: distribution([row[key] for row in rows]) for key in rows[0]}


def audit(root):
    quality = read(root / "quality-suite/result.json")
    by_variant = {v: {} for v in VARIANTS}
    initial_trees = {v: {} for v in VARIANTS[1:]}
    errors = {}
    for cell in quality["cells"]:
        variant = cell["variant"]
        if variant not in VARIANTS:
            continue
        assert cell["status"] == "completed"
        result = read(root / cell["label"] / "result.json")
        assert result["outcome"] == "completed"
        pair = tuple(cell[key] for key in ("backbone", "order", "seed"))
        assert result["cell"] == {
            key: cell[key] for key in ("backbone", "order", "seed", "variant")
        }
        assert pair not in by_variant[variant] and result["completed_steps"] == 512
        phases = {p: utilization(result[p], variant, errors) for p in PHASES}
        if variant in initial_trees:
            initial_trees[variant][pair] = result["initial"]["retrieval"]
        gate = {key: result[key] for key in ("gate_initial", "gate_final", "gate_movement")}
        assert all(math.isfinite(value) for value in gate.values())
        assert gate["gate_initial"] == -2.0
        match(
            gate["gate_movement"],
            gate["gate_final"] - gate["gate_initial"],
            "gate_movement",
            errors,
        )
        movement = result["router_movement_l2"]
        gradient_steps = result["router_nonzero_gradient_steps"]
        with (root / cell["label"] / "metrics.jsonl").open() as stream:
            events = [json.loads(line) for line in stream]
        steps = [event for event in events if event["event"] == "train_step"]
        assert len(steps) == 512
        assert all(math.isfinite(event["gate"]) for event in steps)
        assert steps[-1]["gate"] == gate["gate_final"]
        raw_gradients = [event["pre_clip_router_gradient_norm"] for event in steps]
        if variant == "flat":
            assert (
                movement is None
                and gradient_steps is None
                and all(g is None for g in raw_gradients)
            )
        if variant == "fixed_tree":
            assert (
                movement == 0 and gradient_steps is None and all(g is None for g in raw_gradients)
            )
        if variant == "learned_tree":
            assert math.isfinite(movement) and movement > 0 and gradient_steps == 512
            assert all(math.isfinite(g) and g > 0 for g in raw_gradients)
        by_variant[variant][pair] = {
            "backbone": pair[0],
            "order": pair[1],
            "seed": pair[2],
            **phases,
            "training": {
                **gate,
                "router_movement_l2": movement,
                "router_nonzero_gradient_steps": gradient_steps,
            },
        }

    expected = {
        (b, o, s) for b in (101, 102, 103) for o in (301, 302, 303) for s in (501, 502, 503)
    }
    assert all(set(rows) == expected for rows in by_variant.values())
    assert initial_trees["fixed_tree"] == initial_trees["learned_tree"]
    sorted_rows = {v: [data[p] for p in sorted(expected)] for v, data in by_variant.items()}
    return {
        "status": "PASS",
        "memory_cells": 81,
        "evaluations_checked": 162,
        "paired_tree_initial_records_equal": 27,
        "fixed_router_unchanged_cells": 27,
        "learned_router_positive_movement_cells": 27,
        "learned_router_all_512_nonzero_gradient_cells": 27,
        "absolute_tolerance": ATOL,
        "maximum_observed_reconstruction_error": errors,
        "by_variant": {
            v: {p: summarize([row[p] for row in records]) for p in (*PHASES, "training")}
            for v, records in sorted_rows.items()
        },
        "cells": sorted_rows,
        "limits": (
            "Per-query router entropy is the reported mean; aggregate branch counts "
            "cannot reconstruct it. Router movement uses the saved scalar, and gradient counts "
            "are verified from raw per-step norms; binary states are outside this audit. "
            "Summaries are descriptive and add no scientific gate."
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=ROOT)
    args = parser.parse_args()
    if not __debug__:
        raise RuntimeError("Run with assertions enabled")
    print(json.dumps(audit(args.results), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
