"""Prespecified quality, trace and latency decision arithmetic."""

import math
import statistics
import struct
from collections.abc import Callable
from typing import Any

from .p2_analysis import _distribution
from .p2_config import BACKBONES, ORDERS
from .p5_config import (
    BASELINE,
    CONDITIONS,
    DENSE,
    FIXED,
    FLAT,
    LEARNED,
    MEMORIES,
    SEEDS,
    Cell,
    cells,
)
from .p5_timing import ADDITION, FORWARD

PAIRS = [(b, o, seed) for b in BACKBONES for o in ORDERS for seed in SEEDS]


def _eq(a: float, b: float) -> bool:
    return struct.pack("!d", a) == struct.pack("!d", b)


def _parent_groups(rows: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    return [
        [r for r in rows if (r["backbone"], r["order"]) == (b, o)]
        for b in BACKBONES
        for o in ORDERS
    ]


def _criteria(
    rows: list[dict[str, Any]],
    key: str,
    mean_test: Callable[[float], bool],
    count_test: Callable[[float], bool],
) -> dict[str, bool]:
    values = [r[key] for r in rows]
    return {
        "mean": mean_test(statistics.mean(values)),
        "cells": sum(count_test(v) for v in values) >= 22,
        "parents": sum(
            count_test(statistics.mean(r[key] for r in parent)) for parent in _parent_groups(rows)
        )
        >= 8,
    }


def describe(
    rows: list[dict[str, Any]],
    timing: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    indexed = {}
    for row in rows:
        cell = Cell(row["backbone"], row["order"], row["seed"], row["variant"])
        expected = (
            {"enabled"}
            if cell.variant == BASELINE
            else {"enabled", "disabled"}
            if cell.variant == DENSE
            else set(CONDITIONS)
        )
        if (
            cell in indexed
            or row["interventions"].keys() != expected
            or not all(math.isfinite(v) for v in row["interventions"].values())
            or not math.isfinite(row["final_nll"])
            or not _eq(row["final_nll"], row["interventions"]["enabled"])
            or (cell.variant != BASELINE and not math.isfinite(row["initial_nll"]))
        ):
            raise ValueError("P5 invalid quality row or interventions")
        indexed[cell] = row
    if indexed.keys() != set(cells()):
        raise ValueError("P5 quality analysis requires all 117 registered cells")
    paired: list[dict[str, Any]] = []
    for b, o, seed in PAIRS:
        z = indexed[Cell(b, o, 0, BASELINE)]["final_nll"]
        trained = {v: indexed[Cell(b, o, seed, v)] for v in (*MEMORIES, DENSE)}
        final = {v: record["final_nll"] for v, record in trained.items()}
        for record in trained.values():
            if not _eq(z, record["interventions"]["disabled"]):
                raise ValueError("P5 disabled loss differs from paired baseline")
        row = {
            "backbone": b,
            "order": o,
            "seed": seed,
            "baseline_nll": z,
            "variants": trained,
            "R": final[FIXED] - final[LEARNED],
            "G_dense": z - final[DENSE],
        }
        for v in MEMORIES:
            row[f"G_{v}"] = z - final[v]
            row[f"P_{v}"] = trained[v]["interventions"]["values_permuted"] - final[v]
            row[f"T_{v}"] = final[v] - final[FLAT]
            q = final[DENSE] - final[v]
            if not math.isclose(q, row[f"G_{v}"] - row["G_dense"], abs_tol=1e-12, rel_tol=0):
                raise ValueError("P5 dense contrast identity mismatch")
            row[f"Q_{v}"] = q
        for v, record in trained.items():
            row[f"final_minus_initial_{v}"] = final[v] - record["initial_nll"]
        paired.append(row)
    keys = [
        key
        for key in paired[0]
        if key
        not in (
            "backbone",
            "order",
            "seed",
            "baseline_nll",
            "variants",
        )
    ]
    summary = {key: _distribution([r[key] for r in paired]) for key in keys}
    parents = _parent_groups(paired)
    clauses = {}
    sign_counts = {}
    for v in MEMORIES:
        g, p = f"G_{v}", f"P_{v}"
        count = sum(r[g] > 0 and r[p] > 0 for r in paired)
        parent_count = sum(
            statistics.mean(r[g] for r in group) > 0 and statistics.mean(r[p] for r in group) > 0
            for group in parents
        )
        sign_counts[v] = {"both_positive_cells": count, "both_positive_parents": parent_count}
        clauses[f"U_{v}"] = {
            "mean_gain": summary[g]["mean"] >= 0.005,
            "mean_shuffle": summary[p]["mean"] >= 0.005,
            "cells": count >= 22,
            "parents": parent_count >= 8,
            "mean_final_below_initial": summary[f"final_minus_initial_{v}"]["mean"] < 0,
        }
        clauses[f"dense_tolerance_{v}"] = _criteria(
            paired, f"Q_{v}", lambda x: x >= -0.005, lambda x: x >= -0.005
        )
    clauses["R"] = {
        **_criteria(paired, "R", lambda x: x >= 0.005, lambda x: x > 0),
        "U_learned_tree": all(clauses[f"U_{LEARNED}"].values()),
    }
    for v in (FIXED, LEARNED):
        clauses[f"Q_{v}"] = _criteria(paired, f"T_{v}", lambda x: x <= 0.005, lambda x: x <= 0.005)
    flags = {key: all(values.values()) for key, values in clauses.items()}
    latency, work = timing_analysis(timing) if timing is not None else ({}, {})
    full = (
        flags[f"U_{LEARNED}"]
        and flags["R"]
        and flags[f"Q_{LEARNED}"]
        and work.get(LEARNED, {}).get("passed") is True
        and latency.get(LEARNED, {}).get("status") == "PASS"
    )
    return {
        "quality_clauses": clauses,
        "quality_flags": flags,
        "sign_counts": sign_counts,
        "summary": summary,
        "paired_cells": paired,
        "unique_baselines": [indexed[Cell(b, o, 0, BASELINE)] for b in BACKBONES for o in ORDERS],
        "nll_distributions": {
            v: {
                tag: _distribution([r["variants"][v][f"{tag}_nll"] for r in paired])
                for tag in ("initial", "final")
            }
            for v in (*MEMORIES, DENSE)
        },
        "baseline_nll_distribution": _distribution(
            [indexed[Cell(b, o, 0, BASELINE)]["final_nll"] for b in BACKBONES for o in ORDERS]
        ),
        "per_parent": [
            {
                "backbone": group[0]["backbone"],
                "order": group[0]["order"],
                "means": {key: statistics.mean(r[key] for r in group) for key in keys},
                "seed_effects": [{key: r[key] for key in ("seed", *keys)} for r in group],
            }
            for group in parents
        ],
        "marginal_means": {
            name: {
                str(level): {
                    key: statistics.mean(r[key] for r in paired if r[name] == level) for key in keys
                }
                for level in levels
            }
            for name, levels in (("backbone", BACKBONES), ("order", ORDERS), ("seed", SEEDS))
        },
        "work": work,
        "latency": latency,
        "timing_complete": timing is not None,
        "full_learned_hierarchy_criterion": full if timing is not None else None,
        "limitations": "shared data/parents/seeds; descriptive results, not independent replicas",
    }


def timing_analysis(workers: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    baselines = {(r["backbone"], r["order"]) for r in workers if r["seed"] == 0}
    indexed = {(r["backbone"], r["order"], r["seed"]): r for r in workers if r["seed"] != 0}
    if len(workers) != 36 or len(baselines) != 9 or indexed.keys() != set(PAIRS):
        raise ValueError("P5 timing analysis requires all 36 registered workers")
    latency, work = {}, {}
    for variant in (FIXED, LEARNED):
        scopes = {}
        ratios_all = []
        for scope in (ADDITION, FORWARD):
            rows = []
            for b, o, seed in PAIRS:
                measurements = {
                    r["variant"]: r
                    for r in indexed[b, o, seed]["timing"]["records"]
                    if r["batch_size"] == 8 and r["scope"] == scope
                }
                tree, flat = measurements[variant], measurements[FLAT]
                usable = tree["usable"] and flat["usable"]
                ratio = (
                    tree["median_ns"] / flat["median_ns"]
                    if (tree["median_ns"] > 0 and flat["median_ns"] > 0)
                    else None
                )
                rows.append(
                    {"backbone": b, "order": o, "seed": seed, "ratio": ratio, "usable": usable}
                )
            ratios_all += rows
            reliable = all(row["usable"] for row in rows)
            evidence: dict[str, Any] = {
                "ratios": rows,
                "reliable": reliable,
                "status": "INCONCLUSIVE",
            }
            if all(row["ratio"] is not None for row in rows):
                gm = statistics.geometric_mean(row["ratio"] for row in rows)
                parents = [
                    {
                        "backbone": group[0]["backbone"],
                        "order": group[0]["order"],
                        "ratio": statistics.geometric_mean(row["ratio"] for row in group),
                    }
                    for group in _parent_groups(rows)
                ]
                compare: Callable[[float], bool] = (
                    (lambda x: x < 1) if scope == ADDITION else (lambda x: x <= 1.05)
                )
                clauses = {
                    "geometric_mean": gm <= (0.8 if scope == ADDITION else 1.05),
                    "cells": sum(compare(row["ratio"]) for row in rows) >= 22,
                    "parents": sum(compare(p["ratio"]) for p in parents) >= 8,
                }
                evidence.update(geometric_mean=gm, parents=parents, clauses=clauses)
                if reliable:
                    evidence["status"] = "PASS" if all(clauses.values()) else "FAIL"
            scopes[scope] = evidence
        statuses = {x["status"] for x in scopes.values()}
        latency[variant] = {
            "status": "INCONCLUSIVE"
            if not all(r["usable"] for r in ratios_all)
            else "PASS"
            if statuses == {"PASS"}
            else "FAIL",
            "scopes": scopes,
        }
        audited = []
        for pair in PAIRS:
            trace = indexed[pair]["traces"]
            for size in ("8", "1"):
                for flat, tree in zip(trace[FLAT][size], trace[variant][size], strict=True):
                    score = (
                        tree["key_dot_products_per_query"] + tree["router_dot_products_per_query"]
                    ) / (flat["key_dot_products_per_query"] + flat["router_dot_products_per_query"])
                    logical = (
                        tree["candidate_key_elements_per_query"] + tree["router_elements_per_query"]
                    ) / (
                        flat["candidate_key_elements_per_query"] + flat["router_elements_per_query"]
                    )
                    audited.append(
                        {
                            "score_ratio": score,
                            "logical_ratio": logical,
                            "query_count": tree["queries"],
                            "passed": tree["validated"]
                            and flat["validated"]
                            and score <= 0.25
                            and logical <= 0.25
                            and tree["selected_values_per_query"]
                            == flat["selected_values_per_query"]
                            == 8,
                        }
                    )
        work[variant] = {
            "passed": len(audited) == 27 * 2 * 4 and all(r["passed"] for r in audited),
            "comparison_count": len(audited),
            "comparisons": audited,
        }
    return latency, work
