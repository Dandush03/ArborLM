#!/usr/bin/env python3
"""Independent ADR-0010 arithmetic from compact P5 cell/timing records.

This checker intentionally does not import ArborLM or its analysis module.
It is prepared for post-suite review and must not be run before authorization.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import statistics
import struct
import sys
from pathlib import Path
from typing import Any

BACKBONES = (101, 102, 103)
ORDERS = (301, 302, 303)
SEEDS = (501, 502, 503)
BASELINE, FLAT, FIXED, LEARNED, DENSE = (
    "baseline",
    "flat",
    "fixed_tree",
    "learned_tree",
    "dense",
)
MEMORIES = (FLAT, FIXED, LEARNED)
VARIANTS = (*MEMORIES, DENSE)
CONDITIONS = ("enabled", "disabled", "values_permuted", "joint_within_branch")
ADDITION, FORWARD = "addition_forward", "model_forward"


def read(path: Path) -> Any:
    return json.loads(path.read_text())


def same_float(left: float, right: float) -> bool:
    return struct.pack("!d", left) == struct.pack("!d", right)


def mean(values: list[float]) -> float:
    return statistics.fmean(values)


def nearest_rank(values: list[int], p: float) -> int:
    ordered = sorted(values)
    return ordered[math.ceil(len(ordered) * p) - 1]


def quality_rows(
    results: Path, errors: list[str]
) -> dict[tuple[int, int, int, str], dict[str, Any]]:
    indexed: dict[tuple[int, int, int, str], dict[str, Any]] = {}
    expected = {(b, o, 0, BASELINE) for b in BACKBONES for o in ORDERS} | {
        (b, o, seed, variant)
        for b in BACKBONES
        for o in ORDERS
        for seed in SEEDS
        for variant in (*MEMORIES, DENSE)
    }
    for label_dir in sorted(results.iterdir()):
        if not label_dir.is_dir() or not (label_dir / "result.json").is_file():
            continue
        if not label_dir.name.startswith("b"):
            continue
        if (
            re.fullmatch(
                r"b\d{3}-o\d{3}-(?:baseline|flat-s\d+|fixed_tree-s\d+|learned_tree-s\d+|dense-s\d+)",
                label_dir.name,
            )
            is None
        ):
            errors.append(f"malformed cell-like result directory: {label_dir}")
            continue
        try:
            manifest = read(label_dir / "manifest.json")
            cell = manifest["seeds"]
            key = (cell["backbone"], cell["order"], cell["seed"], cell["variant"])
            result = read(label_dir / "result.json")
            if key in indexed:
                errors.append(f"duplicate quality cell: {key}")
            if result.get("outcome") != "completed" or key not in expected:
                errors.append(f"unregistered or incomplete quality cell: {label_dir}")
            interventions = result["interventions"]
            values = {name: row["nll"] for name, row in interventions.items()}
            required = (
                {"enabled"}
                if cell["variant"] == BASELINE
                else {"enabled", "disabled"}
                if cell["variant"] == DENSE
                else set(CONDITIONS)
            )
            if set(values) != required:
                errors.append(f"wrong intervention set: {label_dir}")
            if not same_float(result["final"]["nll"], values["enabled"]):
                errors.append(f"final and enabled replay differ: {label_dir}")
            if cell["variant"] != BASELINE and result["initial"] is None:
                errors.append(f"missing initial evaluation: {label_dir}")
            metrics_path = label_dir / "metrics.jsonl"
            events = [json.loads(line) for line in metrics_path.read_text().splitlines() if line]
            scientific_events = [
                event
                for event in events
                if event.get("event")
                in ("initial_evaluation", "final_evaluation", "intervention_evaluation")
            ]
            integrity_events = [
                event for event in events if event.get("event") == "parent_restore_integrity"
            ]
            expected_scientific = (
                2 if cell["variant"] == BASELINE else 4 if cell["variant"] == DENSE else 6
            )
            expected_integrity = int(cell["variant"] == BASELINE)
            if (
                len(scientific_events) != expected_scientific
                or len(integrity_events) != expected_integrity
            ):
                errors.append(f"evaluation event count mismatch: {label_dir}")
            if any(
                event.get("training_target_tokens") != 0
                for event in scientific_events + integrity_events
            ):
                errors.append(f"evaluation event has training targets: {label_dir}")
            if any(
                event.get("target_tokens") != 32768
                for event in scientific_events + integrity_events
            ):
                errors.append(f"evaluation target count mismatch: {label_dir}")
            final_events = [
                event for event in scientific_events if event.get("event") == "final_evaluation"
            ]
            initial_events = [
                event for event in scientific_events if event.get("event") == "initial_evaluation"
            ]
            intervention_events = [
                event
                for event in scientific_events
                if event.get("event") == "intervention_evaluation"
            ]
            if len(final_events) != 1 or not same_float(
                final_events[0]["nll"], result["final"]["nll"]
            ):
                errors.append(f"raw final-evaluation NLL differs from result: {label_dir}")
            if result["initial"] is None:
                if initial_events:
                    errors.append(f"unexpected raw initial-evaluation event: {label_dir}")
            elif len(initial_events) != 1 or not same_float(
                initial_events[0]["nll"], result["initial"]["nll"]
            ):
                errors.append(f"raw initial-evaluation NLL differs from result: {label_dir}")
            event_conditions = {event.get("condition"): event for event in intervention_events}
            if set(event_conditions) != set(values):
                errors.append(f"raw/result intervention event set differs: {label_dir}")
            for condition, value in values.items():
                if condition in event_conditions and not same_float(
                    event_conditions[condition]["nll"], value
                ):
                    errors.append(f"raw/result intervention NLL differs: {label_dir}/{condition}")
            train_events = [event for event in events if event.get("event") == "train_step"]
            expected_steps = 0 if cell["variant"] == BASELINE else 512
            if len(train_events) != expected_steps:
                errors.append(f"training update count mismatch: {label_dir}")
            if expected_steps:
                expected_offsets = [((step - 1) * 8) % 2048 for step in range(1, 513)]
                expected_cursor = [step * 8 for step in range(1, 513)]
                expected_targets = [step * 512 for step in range(1, 513)]
                if [event.get("additional_step") for event in train_events] != list(range(1, 513)):
                    errors.append(f"raw training step sequence mismatch: {label_dir}")
                if [
                    event.get("order_offset_for_update") for event in train_events
                ] != expected_offsets:
                    errors.append(f"raw training order-offset sequence mismatch: {label_dir}")
                if [
                    event.get("absolute_order_cursor") for event in train_events
                ] != expected_cursor:
                    errors.append(f"raw training absolute cursor sequence mismatch: {label_dir}")
                if [event.get("next_cyclic_order_cursor") for event in train_events] != [
                    x % 2048 for x in expected_cursor
                ]:
                    errors.append(f"raw training cyclic cursor sequence mismatch: {label_dir}")
                if [event.get("additional_targets") for event in train_events] != expected_targets:
                    errors.append(f"raw cumulative target sequence mismatch: {label_dir}")
            snapshot_steps = (
                {"checkpoint-0"}
                if cell["variant"] == BASELINE
                else {"checkpoint-0", "checkpoint-256", "checkpoint-512"}
            )
            if set(result["checkpoint_state_sha256"]) != snapshot_steps:
                errors.append(f"snapshot count/steps mismatch: {label_dir}")
            if result["additional_training_targets"] != expected_steps * 512:
                errors.append(f"training target count mismatch: {label_dir}")
            row = {
                **cell,
                "final_nll": result["final"]["nll"],
                "initial_nll": result["initial"]["nll"] if result["initial"] else None,
                "final_retrieval": result["final"]["retrieval"],
                "initial_retrieval": result["initial"]["retrieval"] if result["initial"] else None,
                "gate_initial": result.get("gate_initial"),
                "gate_final": result.get("gate_final"),
                "gate_movement": result.get("gate_movement"),
                "router_movement_l2": result.get("router_movement_l2"),
                "interventions": values,
                "targets": result["final"]["target_tokens"],
                "training_targets": result["additional_training_targets"],
                "steps": result["completed_steps"],
                "snapshots": result["checkpoint_state_sha256"],
                "scientific_evaluations": len(scientific_events),
                "integrity_evaluations": len(integrity_events),
                "update_events": len(train_events),
            }
            indexed[key] = row
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"cannot parse quality cell {label_dir}: {exc}")
    if set(indexed) != expected:
        errors.append(f"quality matrix mismatch: expected {len(expected)}, found {len(indexed)}")
    return indexed


def distribution(values: list[float]) -> dict[str, float]:
    return {
        "mean": mean(values),
        "median": statistics.median(values),
        "sample_sd": statistics.stdev(values) if len(values) > 1 else 0.0,
        "min": min(values),
        "max": max(values),
    }


def arithmetic(indexed: dict[tuple[int, int, int, str], dict[str, Any]]) -> dict[str, Any]:
    pairs = []
    for b in BACKBONES:
        for o in ORDERS:
            z = indexed[b, o, 0, BASELINE]["final_nll"]
            for seed in SEEDS:
                baseline = indexed[b, o, 0, BASELINE]
                variants = {v: indexed[b, o, seed, v] for v in (*MEMORIES, DENSE)}
                for variant in MEMORIES:
                    if not same_float(variants[variant]["interventions"]["disabled"], z):
                        raise ValueError(
                            f"disabled loss differs from baseline: {(b, o, seed, variant)}"
                        )
                    if (
                        abs(
                            variants[variant]["interventions"]["joint_within_branch"]
                            - variants[variant]["final_nll"]
                        )
                        > 1e-6
                    ):
                        raise ValueError(
                            f"joint permutation invariance exceeded 1e-6: {(b, o, seed, variant)}"
                        )
                if not same_float(variants[DENSE]["interventions"]["disabled"], z):
                    raise ValueError(f"dense disabled loss differs from baseline: {(b, o, seed)}")
                flat = variants[FLAT]["final_nll"]
                dense = variants[DENSE]["final_nll"]
                row: dict[str, Any] = {
                    "backbone": b,
                    "order": o,
                    "seed": seed,
                    "baseline_nll": z,
                    **{
                        f"final_{variant}": variants[variant]["final_nll"]
                        for variant in (*MEMORIES, DENSE)
                    },
                    **{
                        f"initial_{variant}": variants[variant]["initial_nll"]
                        for variant in (*MEMORIES, DENSE)
                    },
                    "R": variants[FIXED]["final_nll"] - variants[LEARNED]["final_nll"],
                    "G_dense": z - dense,
                }
                for variant in MEMORIES:
                    final = variants[variant]["final_nll"]
                    gain = z - final
                    shuffle = variants[variant]["interventions"]["values_permuted"] - final
                    dense_contrast = dense - final
                    row[f"G_{variant}"] = gain
                    row[f"P_{variant}"] = shuffle
                    row[f"T_{variant}"] = final - flat
                    row[f"Q_{variant}"] = dense_contrast
                    if not math.isclose(
                        dense_contrast,
                        gain - row["G_dense"],
                        rel_tol=0,
                        abs_tol=1e-12,
                    ):
                        raise ValueError(
                            f"dense contrast identity mismatch: {(b, o, seed, variant)}"
                        )
                    row[f"final_minus_initial_{variant}"] = final - variants[variant]["initial_nll"]
                row["final_minus_initial_dense"] = dense - variants[DENSE]["initial_nll"]
                row["variants"] = variants
                row["baseline"] = baseline
                pairs.append(row)
    parents = [
        [row for row in pairs if (row["backbone"], row["order"]) == (b, o)]
        for b in BACKBONES
        for o in ORDERS
    ]
    summaries = {
        key: distribution([row[key] for row in pairs])
        for key in pairs[0]
        if key not in {"backbone", "order", "seed", "baseline_nll", "variants", "baseline"}
    }
    clauses: dict[str, Any] = {}
    for variant in MEMORIES:
        gains, shuffles = (
            [row[f"G_{variant}"] for row in pairs],
            [row[f"P_{variant}"] for row in pairs],
        )
        both = sum(g > 0 and p > 0 for g, p in zip(gains, shuffles, strict=True))
        parent_both = sum(
            mean([r[f"G_{variant}"] for r in group]) > 0
            and mean([r[f"P_{variant}"] for r in group]) > 0
            for group in parents
        )
        clauses[f"U_{variant}"] = {
            "mean_gain": mean(gains) >= 0.005,
            "mean_shuffle": mean(shuffles) >= 0.005,
            "cells_both_positive": both >= 22,
            "parents_both_positive": parent_both >= 8,
            "final_below_initial": summaries[f"final_minus_initial_{variant}"]["mean"] < 0,
            "count_cells_both_positive": both,
            "count_parents_both_positive": parent_both,
        }
        q = [row[f"Q_{variant}"] for row in pairs]
        parent_q = [mean([row[f"Q_{variant}"] for row in group]) for group in parents]
        clauses[f"dense_tolerance_{variant}"] = {
            "mean": mean(q) >= -0.005,
            "cells": sum(value >= -0.005 for value in q) >= 22,
            "parents": sum(value >= -0.005 for value in parent_q) >= 8,
        }
    r = [row["R"] for row in pairs]
    parent_r = [mean([row["R"] for row in group]) for group in parents]
    clauses["R"] = {
        "mean": mean(r) >= 0.005,
        "cells": sum(value > 0 for value in r) >= 22,
        "parents": sum(value > 0 for value in parent_r) >= 8,
        "U_learned_tree": all(
            value for key, value in clauses[f"U_{LEARNED}"].items() if not key.startswith("count_")
        ),
    }
    sign_counts = {
        "R": {
            "positive_cells": sum(value > 0 for value in r),
            "positive_parent_means": sum(value > 0 for value in parent_r),
        }
    }
    for variant in MEMORIES:
        gains = [row[f"G_{variant}"] for row in pairs]
        shuffles = [row[f"P_{variant}"] for row in pairs]
        sign_counts[variant] = {
            "gain_positive_cells": sum(value > 0 for value in gains),
            "shuffle_positive_cells": sum(value > 0 for value in shuffles),
            "both_positive_cells": sum(
                gain > 0 and shuffle > 0 for gain, shuffle in zip(gains, shuffles, strict=True)
            ),
            "gain_positive_parent_means": sum(
                mean([row[f"G_{variant}"] for row in group]) > 0 for group in parents
            ),
            "shuffle_positive_parent_means": sum(
                mean([row[f"P_{variant}"] for row in group]) > 0 for group in parents
            ),
        }
    for variant in (FIXED, LEARNED):
        t = [row[f"T_{variant}"] for row in pairs]
        parent_t = [mean([row[f"T_{variant}"] for row in group]) for group in parents]
        clauses[f"Q_{variant}"] = {
            "mean": mean(t) <= 0.005,
            "cells": sum(value <= 0.005 for value in t) >= 22,
            "parents": sum(value <= 0.005 for value in parent_t) >= 8,
        }
    flags = {
        name: all(value for key, value in clause.items() if not key.startswith("count_"))
        for name, clause in clauses.items()
    }
    return {
        "paired_count": len(pairs),
        "paired": pairs,
        "summary": summaries,
        "baseline_nll_distribution": distribution(
            [indexed[b, o, 0, BASELINE]["final_nll"] for b in BACKBONES for o in ORDERS]
        ),
        "baseline_nll_by_parent": [
            {
                "backbone": b,
                "order": o,
                "baseline_nll": indexed[b, o, 0, BASELINE]["final_nll"],
            }
            for b in BACKBONES
            for o in ORDERS
        ],
        "quality_clauses": clauses,
        "quality_flags": flags,
        "sign_counts": sign_counts,
        "per_parent_means": [
            {
                "backbone": group[0]["backbone"],
                "order": group[0]["order"],
                "means": {key: mean([row[key] for row in group]) for key in summaries},
            }
            for group in parents
        ],
        "marginal_means": {
            factor: {
                str(level): {
                    key: mean([row[key] for row in pairs if row[factor] == level])
                    for key in summaries
                }
                for level in levels
            }
            for factor, levels in (
                ("backbone", BACKBONES),
                ("order", ORDERS),
                ("seed", SEEDS),
            )
        },
    }


def retrieval_audit(
    indexed: dict[tuple[int, int, int, str], dict[str, Any]], errors: list[str]
) -> dict[str, Any]:
    per_cell = []

    def entropy(counts: list[int]) -> tuple[float, float, float, int]:
        total = sum(counts)
        probabilities = [count / total for count in counts if count]
        h = -math.fsum(p * math.log(p) for p in probabilities)
        return math.exp(h), h / math.log(len(counts)), max(counts) / total, len(probabilities)

    for key, row in indexed.items():
        b, o, seed, variant = key
        if variant == BASELINE:
            continue
        retrieval_sets = [("final", row["final_retrieval"])]
        if row["initial_nll"] is not None:
            retrieval_sets.insert(0, ("initial", row["initial_retrieval"]))
        for phase, retrieval in retrieval_sets:
            if retrieval is None:
                per_cell.append(
                    {
                        "backbone": b,
                        "order": o,
                        "seed": seed,
                        "variant": variant,
                        "phase": phase,
                        "nll": row["final_nll"] if phase == "final" else row["initial_nll"],
                        "gate_initial": row["gate_initial"],
                        "gate_final": row["gate_final"],
                        "gate_movement": row["gate_movement"],
                        "router_movement_l2": row["router_movement_l2"],
                    }
                )
                continue
            slots = retrieval.get("selected_slot_counts")
            if (
                not isinstance(slots, list)
                or len(slots) != 4096
                or retrieval.get("queries") != 32768
            ):
                errors.append(f"retrieval slot-count dimensions mismatch: {key}/{phase}")
                continue
            if sum(slots) != 262144:
                errors.append(f"retrieval selected-slot total mismatch: {key}/{phase}")
            effective, normalized, hottest, unique = entropy(slots)
            derived = {
                "effective_selected_slots": effective,
                "selected_slot_entropy_normalized": normalized,
                "hottest_selected_slot_fraction": hottest,
                "unique_selected_slots": unique,
            }
            for name, value in derived.items():
                reported = retrieval.get(name)
                if not isinstance(reported, int | float) or not math.isclose(
                    float(reported), value, rel_tol=0, abs_tol=1e-12
                ):
                    errors.append(f"retrieval count-derived metric mismatch: {key}/{phase}/{name}")
            router_derived = {}
            router = retrieval.get("router")
            if variant in (FIXED, LEARNED):
                if not isinstance(router, dict):
                    errors.append(f"memory retrieval router metrics missing: {key}/{phase}")
                    continue
                branch_counts = router.get("selected_value_branch_counts")
                top_counts = router.get("top1_branch_counts")
                visited_counts = router.get("visited_branch_counts")
                if (
                    not isinstance(branch_counts, list)
                    or len(branch_counts) != 16
                    or not isinstance(top_counts, list)
                    or len(top_counts) != 16
                    or not isinstance(visited_counts, list)
                    or len(visited_counts) != 16
                ):
                    errors.append(f"router count dimensions mismatch: {key}/{phase}")
                    continue
                slot_branches = [
                    sum(slots[branch * 256 : (branch + 1) * 256]) for branch in range(16)
                ]
                if branch_counts != slot_branches or sum(branch_counts) != 262144:
                    errors.append(f"router selected-value branch counts mismatch: {key}/{phase}")
                if sum(top_counts) != 32768 or sum(visited_counts) != 65536:
                    errors.append(f"router top1/visited totals mismatch: {key}/{phase}")
                top_effective, top_entropy, top_hottest, top_unique = entropy(top_counts)
                del top_effective
                router_derived = {
                    "normalized_top1_entropy": top_entropy,
                    "hottest_top1_branch_fraction": top_hottest,
                    "nonzero_top1_branches": top_unique,
                }
                for name, value in router_derived.items():
                    if not math.isclose(float(router.get(name)), value, rel_tol=0, abs_tol=1e-12):
                        errors.append(f"router count-derived metric mismatch: {key}/{phase}/{name}")
            per_cell.append(
                {
                    "backbone": b,
                    "order": o,
                    "seed": seed,
                    "variant": variant,
                    "phase": phase,
                    **derived,
                    **router_derived,
                    "reported_mean_normalized_query_router_entropy": (
                        router.get("mean_normalized_query_router_entropy")
                        if isinstance(router, dict)
                        else None
                    ),
                    "nll": row["final_nll"] if phase == "final" else row["initial_nll"],
                    "gate_initial": row["gate_initial"],
                    "gate_final": row["gate_final"],
                    "gate_movement": row["gate_movement"],
                    "router_movement_l2": row["router_movement_l2"],
                }
            )
    summary = {}
    descriptive_metrics = (
        "nll",
        "effective_selected_slots",
        "selected_slot_entropy_normalized",
        "hottest_selected_slot_fraction",
        "unique_selected_slots",
        "normalized_top1_entropy",
        "hottest_top1_branch_fraction",
        "nonzero_top1_branches",
        "reported_mean_normalized_query_router_entropy",
        "gate_initial",
        "gate_final",
        "gate_movement",
        "router_movement_l2",
    )
    for variant in VARIANTS:
        group = [row for row in per_cell if row["variant"] == variant]
        summary[variant] = {}
        for phase in ("initial", "final"):
            phase_rows = [row for row in group if row["phase"] == phase]
            for metric in descriptive_metrics:
                values = [float(row[metric]) for row in phase_rows if row.get(metric) is not None]
                if values:
                    summary[variant][f"{phase}_{metric}"] = distribution(values)
    return {"per_cell": per_cell, "descriptive_by_variant": summary}


def timing_records(
    timing_root: Path, errors: list[str]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    records = []
    expected = {(b, o, 0) for b in BACKBONES for o in ORDERS} | {
        (b, o, seed) for b in BACKBONES for o in ORDERS for seed in SEEDS
    }
    for path in sorted(timing_root.glob("*/result.json")):
        try:
            report = read(path)
            b, o, seed = report["backbone"], report["order"], report["seed"]
            if report.get("outcome") != "completed" or (b, o, seed) not in expected:
                errors.append(f"invalid timing worker result: {path}")
            event_path = path.parent / "metrics.jsonl"
            events = [json.loads(line) for line in event_path.read_text().splitlines() if line]
            blocks = [event for event in events if event.get("event") == "timing_block"]
            expected_blocks = 16 if seed == 0 else 176
            if len(blocks) != expected_blocks:
                errors.append(f"timing raw block count mismatch: {path.parent}")
            raw_warmups = sum(len(event.get("warmup_input_indexes", [])) for event in blocks)
            raw_timed = sum(len(event.get("durations_ns", [])) for event in blocks)
            if any(
                len(event.get("warmup_input_indexes", [])) != 2
                or len(event.get("durations_ns", [])) != 10
                for event in blocks
            ):
                errors.append(f"timing raw block repetition mismatch: {path.parent}")
            if (
                raw_warmups != report["timing"]["call_counts"]["warmups"]
                or raw_timed != report["timing"]["call_counts"]["timed"]
            ):
                errors.append(f"timing raw events disagree with call counts: {path.parent}")
            raw_groups: dict[tuple[int, str, str], dict[int, list[int]]] = {}
            for event in blocks:
                group_key = (event["batch_size"], event["scope"], event["variant"])
                round_id = event["round"]
                group = raw_groups.setdefault(group_key, {})
                if round_id in group:
                    errors.append(
                        "duplicate timing scope round in raw events: "
                        f"{path.parent}/{group_key}/{round_id}"
                    )
                group[round_id] = event["durations_ns"]
            index = (b - 101) * 9 + (o - 301) * 3 + (seed - 501) if seed else 0
            variants = ("baseline",) if seed == 0 else (*MEMORIES, "dense")
            expected_blocks = []
            for batch_size in (8, 1):
                for scope in ("lookup_score_select", ADDITION, FORWARD):
                    valid = tuple(
                        variant
                        for variant in variants
                        if scope == FORWARD
                        or variant in MEMORIES
                        or (scope == ADDITION and variant == "dense")
                    )
                    for round_id in range(8):
                        shift = (index + round_id) % len(valid) if valid else 0
                        ordered = valid[shift:] + valid[:shift]
                        for variant in ordered:
                            expected_blocks.append(
                                (
                                    batch_size,
                                    scope,
                                    round_id,
                                    variant,
                                    [(round_id * 2 + j) % 4 for j in range(2)],
                                    [(round_id * 10 + j) % 4 for j in range(10)],
                                )
                            )
            actual_blocks = [
                (
                    event["batch_size"],
                    event["scope"],
                    event["round"],
                    event["variant"],
                    event["warmup_input_indexes"],
                    event["timed_input_indexes"],
                )
                for event in blocks
            ]
            if actual_blocks != expected_blocks:
                errors.append(f"raw timing schedule/input-rotation mismatch: {path.parent}")
            raw_summaries = {}
            resolution = report["timing"]["clock"]["resolution_ns"]
            reported = {
                (entry["batch_size"], entry["scope"], entry["variant"]): entry
                for entry in report["timing"]["records"]
            }
            if len(reported) != len(report["timing"]["records"]):
                errors.append(f"duplicate timing summary records: {path.parent}")
            for group_key, rounds in raw_groups.items():
                if set(rounds) != set(range(8)) or any(
                    len(values) != 10 for values in rounds.values()
                ):
                    errors.append(
                        f"raw timing rounds/repetitions differ: {path.parent}/{group_key}"
                    )
                    continue
                raw_rounds = [rounds[index] for index in range(8)]
                durations = [value for values in raw_rounds for value in values]
                round_medians = [statistics.median(values) for values in raw_rounds]
                median = statistics.median(durations)
                min_round = min(round_medians)
                round_ratio = max(round_medians) / min_round if min_round > 0 else None
                criteria = {
                    "positive_durations": min(durations) > 0,
                    "above_clock_resolution": median >= 100 * resolution,
                    "stable_rounds": round_ratio is not None and round_ratio <= 1.25,
                }
                raw_summary = {
                    "durations_ns": durations,
                    "round_medians_ns": round_medians,
                    "median_ns": median,
                    "min_ns": min(durations),
                    "max_ns": max(durations),
                    "p10_ns": nearest_rank(durations, 0.10),
                    "p90_ns": nearest_rank(durations, 0.90),
                    "p95_ns": nearest_rank(durations, 0.95),
                    "round_median_ratio": round_ratio,
                    "resolution_ns": resolution,
                    "reliability_criteria": criteria,
                    "usable": all(criteria.values()),
                }
                raw_summaries[group_key] = raw_summary
                aggregate = reported.get(group_key)
                if aggregate is None:
                    errors.append(
                        f"raw timing group absent from summary: {path.parent}/{group_key}"
                    )
                    continue
                for name, value in raw_summary.items():
                    if aggregate.get(name) != value:
                        errors.append(
                            "raw timing summary differs from report: "
                            f"{path.parent}/{group_key}/{name}"
                        )
            if set(raw_summaries) != set(reported):
                errors.append(f"raw timing scope coverage differs from report: {path.parent}")
            expected_keys = (
                {(size, FORWARD, "baseline") for size in (8, 1)}
                if seed == 0
                else {
                    *(
                        (size, "lookup_score_select", variant)
                        for size in (8, 1)
                        for variant in MEMORIES
                    ),
                    *(
                        (size, ADDITION, variant)
                        for size in (8, 1)
                        for variant in (*MEMORIES, "dense")
                    ),
                    *(
                        (size, FORWARD, variant)
                        for size in (8, 1)
                        for variant in (*MEMORIES, "dense")
                    ),
                }
            )
            if set(raw_summaries) != expected_keys:
                errors.append(f"registered raw timing scopes/variants mismatch: {path.parent}")
            report["_raw_block_count"] = len(blocks)
            report["_raw_warmups"] = raw_warmups
            report["_raw_timed"] = raw_timed
            report["_raw_summaries"] = raw_summaries
            records.append(report)
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            errors.append(f"cannot parse timing result {path}: {exc}")
    if len(records) != 36 or {(r["backbone"], r["order"], r["seed"]) for r in records} != expected:
        errors.append(f"timing worker matrix mismatch: found {len(records)}")
    return records, {"expected_workers": len(expected)}


def summarize_timing(reports: list[dict[str, Any]], errors: list[str]) -> dict[str, Any]:
    timing_totals = {"warmups": 0, "timed": 0, "workers": len(reports)}
    indexed = {}
    worker_audit = []
    for report in reports:
        key = (report["backbone"], report["order"], report["seed"])
        indexed[key] = report
        counts = report["timing"]["call_counts"]
        timing_totals["warmups"] += counts["warmups"]
        timing_totals["timed"] += counts["timed"]
        expected_calls = 192 if report["seed"] == 0 else 2112
        if (
            report["timing_scope_calls"] != expected_calls
            or counts["warmups"] + counts["timed"] != expected_calls
        ):
            errors.append(f"timing call count mismatch {key}")
        worker_audit.append(
            {
                "cell": key,
                "calls": report["timing_scope_calls"],
                "event_count": report["_raw_block_count"],
                "raw_warmups": report["_raw_warmups"],
                "raw_timed": report["_raw_timed"],
            }
        )
    if timing_totals["warmups"] + timing_totals["timed"] != 58752:
        errors.append("suite raw warmup+timed call total != 58,752")

    comparisons = {}
    for variant in (FIXED, LEARNED):
        variant_comparisons = {}
        for scope in (ADDITION, FORWARD):
            ratios, usable = [], []
            for b in BACKBONES:
                for o in ORDERS:
                    for seed in SEEDS:
                        report = indexed[b, o, seed]
                        target = report["_raw_summaries"][8, scope, variant]
                        flat = report["_raw_summaries"][8, scope, FLAT]
                        ratio = (
                            target["median_ns"] / flat["median_ns"]
                            if target["median_ns"] > 0 and flat["median_ns"] > 0
                            else None
                        )
                        ratios.append({"backbone": b, "order": o, "seed": seed, "ratio": ratio})
                        usable.append(target["usable"] and flat["usable"])
            valid_ratios = [row["ratio"] for row in ratios if row["ratio"] is not None]
            geometric_mean = (
                math.exp(mean([math.log(value) for value in valid_ratios]))
                if len(valid_ratios) == len(ratios)
                else None
            )
            parents = []
            for b, o in ((b, o) for b in BACKBONES for o in ORDERS):
                values = [
                    row["ratio"] for row in ratios if (row["backbone"], row["order"]) == (b, o)
                ]
                parents.append(
                    math.exp(mean([math.log(value) for value in values]))
                    if all(value is not None for value in values)
                    else None
                )
            compare = (
                (lambda value: value < 1) if scope == ADDITION else (lambda value: value <= 1.05)
            )
            clauses = None
            if geometric_mean is not None and all(value is not None for value in parents):
                clauses = {
                    "geometric_mean": geometric_mean <= (0.8 if scope == ADDITION else 1.05),
                    "cells": sum(compare(row["ratio"]) for row in ratios) >= 22,
                    "parents": sum(compare(value) for value in parents) >= 8,
                }
            status = (
                "INCONCLUSIVE"
                if not all(usable) or clauses is None
                else "PASS"
                if all(clauses.values())
                else "FAIL"
            )
            variant_comparisons[scope] = {
                "ratios": ratios,
                "geometric_mean": geometric_mean,
                "clauses": clauses,
                "all_27_pairs_reliable": all(usable),
                "status": status,
            }
        comparisons[variant] = variant_comparisons
    work = {}
    for variant in (FIXED, LEARNED):
        audited = []
        for b in BACKBONES:
            for o in ORDERS:
                for seed in SEEDS:
                    traces = indexed[b, o, seed]["traces"]
                    for size in ("8", "1"):
                        flat_records = traces[FLAT][size]
                        tree_records = traces[variant][size]
                        if len(flat_records) != 4 or len(tree_records) != 4:
                            errors.append(
                                f"timing trace sample count mismatch: {(b, o, seed, size)}"
                            )
                        for flat, tree in zip(flat_records, tree_records, strict=True):
                            score_denominator = (
                                flat["key_dot_products_per_query"]
                                + flat["router_dot_products_per_query"]
                            )
                            score_numerator = (
                                tree["key_dot_products_per_query"]
                                + tree["router_dot_products_per_query"]
                            )
                            logical_denominator = (
                                flat["candidate_key_elements_per_query"]
                                + flat["router_elements_per_query"]
                            )
                            logical_numerator = (
                                tree["candidate_key_elements_per_query"]
                                + tree["router_elements_per_query"]
                            )
                            score_ratio = score_numerator / score_denominator
                            logical_ratio = logical_numerator / logical_denominator
                            passed = (
                                flat["validated"]
                                and tree["validated"]
                                and score_ratio <= 0.25
                                and logical_ratio <= 0.25
                                and flat["selected_values_per_query"]
                                == tree["selected_values_per_query"]
                                == 8
                                and flat["queries"] == tree["queries"]
                            )
                            audited.append(
                                {
                                    "backbone": b,
                                    "order": o,
                                    "seed": seed,
                                    "batch_size": int(size),
                                    "score_ratio": score_ratio,
                                    "logical_ratio": logical_ratio,
                                    "passed": passed,
                                }
                            )
        work[variant] = {
            "comparison_count": len(audited),
            "passed": len(audited) == 216 and all(row["passed"] for row in audited),
            "comparisons": audited,
        }
    return {
        "totals": timing_totals,
        "worker_audit": worker_audit,
        "comparisons": comparisons,
        "work": work,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, default=Path("results/p5-2026-11-13"))
    parser.add_argument("--timing", type=Path, default=Path("results/p5-2026-11-13/timing"))
    args = parser.parse_args()
    errors: list[str] = []
    indexed = quality_rows(args.results, errors)
    quality = arithmetic(indexed) if indexed else {}
    retrieval = retrieval_audit(indexed, errors) if indexed else {}
    reports, _ = timing_records(args.timing, errors)
    timing = summarize_timing(reports, errors) if reports else {}
    total_scientific_evaluations = sum(row["scientific_evaluations"] for row in indexed.values())
    total_integrity_evaluations = sum(row["integrity_evaluations"] for row in indexed.values())
    total_updates = sum(row["update_events"] for row in indexed.values())
    total_snapshots = sum(len(row["snapshots"]) for row in indexed.values())
    if (
        total_scientific_evaluations,
        total_integrity_evaluations,
        total_updates,
        total_snapshots,
    ) != (
        612,
        9,
        55296,
        333,
    ):
        errors.append("suite evaluation/update/snapshot totals mismatch")
    output = {
        "audit": "independent ADR-0010 arithmetic",
        "implementation_analysis_imported": False,
        "quality": quality,
        "retrieval_descriptives": retrieval,
        "timing": timing,
        "accounting": {
            "scientific_evaluations": total_scientific_evaluations,
            "parent_integrity_evaluations": total_integrity_evaluations,
            "updates": total_updates,
            "snapshots": total_snapshots,
            "scientific_evaluation_targets": total_scientific_evaluations * 32768,
            "integrity_evaluation_targets": total_integrity_evaluations * 32768,
            "training_targets": sum(row["training_targets"] for row in indexed.values()),
        },
        "errors": errors,
        "status": "PASS" if not errors else "FAIL",
    }
    print(json.dumps(output, sort_keys=True, separators=(",", ":")))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
