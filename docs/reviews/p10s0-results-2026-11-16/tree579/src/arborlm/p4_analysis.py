"""Prespecified P4 parent-paired summaries and descriptive flags."""

import math
import statistics
import struct
from typing import Any

from .p2_analysis import _distribution
from .p2_config import BACKBONES, ORDERS
from .p4_config import BASELINE, CONDITIONS, DENSE, MEMORY, SEEDS, THRESHOLD, TOLERANCE, Cell, cells

EFFECTS = ("C", "D", "P", "C_dense", "Q")


def _mean(rows: list[dict[str, Any]]) -> dict[str, float]:
    return {key: statistics.mean(row[key] for row in rows) for key in EFFECTS}


def _eq(a: float, b: float) -> bool:
    return struct.pack("!d", a) == struct.pack("!d", b)


def describe(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_cell = {}
    for row in rows:
        cell = Cell(row["backbone"], row["order"], row["seed"], row["variant"])
        required = (
            set(CONDITIONS)
            if cell.variant == MEMORY
            else {"enabled", "disabled"}
            if cell.variant == DENSE
            else {"enabled"}
        )
        if (
            cell in by_cell
            or row["interventions"].keys() != required
            or not all(math.isfinite(value) for value in row["interventions"].values())
            or not math.isfinite(row["final_nll"])
            or not _eq(row["final_nll"], row["interventions"]["enabled"])
            or (cell.variant != BASELINE and not math.isfinite(row["initial_nll"]))
        ):
            raise ValueError("invalid P4 row/conditions")
        by_cell[cell] = row
    if by_cell.keys() != set(cells()):
        raise ValueError("P4 analysis requires all 63 registered cells")
    paired: list[dict[str, Any]] = []
    baselines: list[dict[str, Any]] = []
    for b in BACKBONES:
        for o in ORDERS:
            base = by_cell[Cell(b, o, 0, BASELINE)]
            baseline = base["final_nll"]
            baselines.append(base)
            for seed in SEEDS:
                mem = by_cell[Cell(b, o, seed, MEMORY)]
                dense = by_cell[Cell(b, o, seed, DENSE)]
                h, a = mem["final_nll"], dense["final_nll"]
                disabled = mem["interventions"]["disabled"]
                if not _eq(disabled, baseline) or not _eq(
                    dense["interventions"]["disabled"], baseline
                ):
                    raise ValueError("P4 disabled models must equal their baseline bitwise")
                c, d, p, c_dense, q = (
                    baseline - h,
                    disabled - h,
                    mem["interventions"]["values_permuted"] - h,
                    baseline - a,
                    a - h,
                )
                if c != d or not math.isclose(q, c - c_dense, abs_tol=1e-12, rel_tol=0):
                    raise ValueError("P4 paired identity failure")
                paired.append(
                    {
                        "backbone": b,
                        "order": o,
                        "seed": seed,
                        "baseline_nll": baseline,
                        "memory": mem,
                        "dense": dense,
                        "C": c,
                        "D": d,
                        "P": p,
                        "C_dense": c_dense,
                        "Q": q,
                        "memory_final_minus_initial": h - mem["initial_nll"],
                        "dense_final_minus_initial": a - dense["initial_nll"],
                    }
                )
    parents: list[dict[str, Any]] = []
    for b in BACKBONES:
        for o in ORDERS:
            values = [row for row in paired if row["backbone"] == b and row["order"] == o]
            parents.append(
                {
                    "backbone": b,
                    "order": o,
                    "means": _mean(values),
                    "seeds": [
                        {"seed": row["seed"], **{key: row[key] for key in EFFECTS}}
                        for row in values
                    ],
                }
            )
    summary = {key: _distribution([row[key] for row in paired]) for key in EFFECTS}
    counts = {
        "C_positive_cells": sum(row["C"] > 0 for row in paired),
        "C_and_P_positive_cells": sum(row["C"] > 0 and row["P"] > 0 for row in paired),
        "Q_tolerance_cells": sum(row["Q"] >= TOLERANCE for row in paired),
        "Q_positive_cells": sum(row["Q"] > 0 for row in paired),
        "C_positive_parents": sum(row["means"]["C"] > 0 for row in parents),
        "P_positive_parents": sum(row["means"]["P"] > 0 for row in parents),
        "Q_tolerance_parents": sum(row["means"]["Q"] >= TOLERANCE for row in parents),
        "Q_positive_parents": sum(row["means"]["Q"] > 0 for row in parents),
    }
    initial_h = statistics.mean(row["memory"]["initial_nll"] for row in paired)
    final_h = statistics.mean(row["memory"]["final_nll"] for row in paired)
    clauses = {
        "added_predictive_capacity": {
            "mean_C_at_threshold": summary["C"]["mean"] >= THRESHOLD,
            "C_positive_cells": counts["C_positive_cells"] >= 22,
            "C_positive_parents": counts["C_positive_parents"] >= 8,
            "mean_H_final_below_initial": final_h < initial_h,
        },
        "useful_slot_association_dependence": {
            "mean_P_at_threshold": summary["P"]["mean"] >= THRESHOLD,
            "C_and_P_positive_cells": counts["C_and_P_positive_cells"] >= 22,
            "P_positive_parents": counts["P_positive_parents"] >= 8,
        },
        "within_dense_quality_tolerance": {
            "mean_Q_at_tolerance": summary["Q"]["mean"] >= TOLERANCE,
            "Q_tolerance_cells": counts["Q_tolerance_cells"] >= 22,
            "Q_tolerance_parents": counts["Q_tolerance_parents"] >= 8,
        },
        "secondary_memory_advantage": {
            "mean_Q_at_advantage_threshold": summary["Q"]["mean"] >= THRESHOLD,
            "Q_positive_cells": counts["Q_positive_cells"] >= 22,
            "Q_positive_parents": counts["Q_positive_parents"] >= 8,
        },
    }
    flags = {name: all(values.values()) for name, values in clauses.items()}
    return {
        "paired_cells": paired,
        "unique_baselines": baselines,
        "baseline_nll": _distribution([row["final_nll"] for row in baselines]),
        "summary": summary,
        "counts": counts,
        "clauses": clauses,
        "flags": flags,
        "memory_nll": {
            "initial": _distribution([row["memory"]["initial_nll"] for row in paired]),
            "final": _distribution([row["memory"]["final_nll"] for row in paired]),
            "final_minus_initial": _distribution(
                [row["memory_final_minus_initial"] for row in paired]
            ),
        },
        "dense_nll": {
            "initial": _distribution([row["dense"]["initial_nll"] for row in paired]),
            "final": _distribution([row["dense"]["final_nll"] for row in paired]),
            "final_minus_initial": _distribution(
                [row["dense_final_minus_initial"] for row in paired]
            ),
        },
        "per_parent": parents,
        "marginal_means": {
            name: {
                str(value): _mean([row for row in paired if row[name] == value]) for value in levels
            }
            for name, levels in (("backbone", BACKBONES), ("order", ORDERS), ("seed", SEEDS))
        },
        "composite_success": all(
            flags[key]
            for key in (
                "added_predictive_capacity",
                "useful_slot_association_dependence",
                "within_dense_quality_tolerance",
            )
        ),
        "limitations": "shared parents/data/seeds; descriptive thresholds, no significance or "
        "independent-replicate confidence intervals; P1–P3 outcomes unchanged",
    }
