"""Prespecified descriptive decomposition for the balanced P2 grid."""

import math
import statistics
from collections.abc import Sequence
from typing import Any

from .p2_config import ADDITIVE_ATOL, BACKBONES, MEMORIES, ORDERS, THRESHOLD

FACTORS = {"backbone": BACKBONES, "memory": MEMORIES, "order": ORDERS}
RAW = ("enabled", "disabled", "values_permuted", "joint_within_branch", "control")


def _distribution(values: Sequence[float]) -> dict[str, float | int]:
    return {
        "mean": statistics.mean(values),
        "sample_sd": statistics.stdev(values),
        "minimum": min(values),
        "maximum": max(values),
        "positive": sum(v > 0 for v in values),
        "zero": sum(v == 0 for v in values),
        "negative": sum(v < 0 for v in values),
    }


def decompose(rows: list[dict[str, Any]], metric: str) -> dict[str, Any]:
    grand = statistics.mean(float(row[metric]) for row in rows)
    marginal = {
        factor: {
            level: statistics.mean(float(row[metric]) for row in rows if row[factor] == level)
            for level in levels
        }
        for factor, levels in FACTORS.items()
    }
    residuals = []
    for row in rows:
        fitted = grand + sum(means[row[factor]] - grand for factor, means in marginal.items())
        residuals.append((row[metric] - fitted) ** 2)
    return {
        "grand_mean": grand,
        "marginal_means": {
            factor: {str(level): value for level, value in levels.items()}
            for factor, levels in marginal.items()
        },
        "marginal_ranges": {
            factor: max(levels.values()) - min(levels.values())
            for factor, levels in marginal.items()
        },
        "interaction_rms": math.sqrt(statistics.mean(residuals)),
    }


def describe(rows: list[dict[str, Any]]) -> dict[str, Any]:
    expected = {(b, m, o) for b in BACKBONES for m in MEMORIES for o in ORDERS}
    observed = {(row["backbone"], row["memory"], row["order"]) for row in rows}
    if len(rows) != len(expected) or observed != expected:
        raise ValueError("P2 descriptive analysis requires all 27 unique learned cells")
    measured = []
    controls: dict[tuple[int, int], float] = {}
    for row in rows:
        if not all(math.isfinite(row[name]) for name in RAW):
            raise ValueError("P2 raw NLLs must be finite")
        pair = (row["backbone"], row["order"])
        if controls.setdefault(pair, row["control"]) != row["control"]:
            raise ValueError("P2 learned cells must share their registered paired control")
        d = row["disabled"] - row["enabled"]
        p = row["values_permuted"] - row["enabled"]
        g = row["control"] - row["enabled"]
        s = row["control"] - row["disabled"]
        if not math.isclose(g, d + s, rel_tol=0, abs_tol=ADDITIVE_ATOL):
            raise ValueError("P2 identity G = D + S failed")
        measured.append({**row, "D": d, "P": p, "G": g, "S": s})
    distributions = {metric: _distribution([row[metric] for row in measured]) for metric in "DPGS"}
    raw_distributions = {metric: _distribution([row[metric] for row in measured]) for metric in RAW}
    effects = {metric: decompose(measured, metric) for metric in ("D", "G")}
    both_positive = sum(row["D"] > 0 and row["P"] > 0 for row in measured)
    both_useful = sum(row["D"] >= THRESHOLD and row["P"] >= THRESHOLD for row in measured)
    either_nonpositive = sum(row["D"] <= 0 or row["P"] <= 0 for row in measured)
    qualifying = [
        factor for factor, extent in effects["D"]["marginal_ranges"].items() if extent >= THRESHOLD
    ]
    if effects["D"]["interaction_rms"] >= THRESHOLD:
        qualifying.append("combined_interaction")
    consistent = (
        distributions["D"]["mean"] >= THRESHOLD
        and distributions["P"]["mean"] >= THRESHOLD
        and both_positive >= 22
    )
    heterogeneous = both_useful >= 3 and either_nonpositive >= 3
    return {
        "learned_cells": measured,
        "independent_control_runs": 9,
        "summary": distributions,
        "raw_nll_summary_over_paired_cells": raw_distributions,
        "factor_decomposition": effects,
        "counts": {
            "both_positive": both_positive,
            "both_at_least_threshold": both_useful,
            "either_nonpositive": either_nonpositive,
        },
        "flags": {
            "consistent_dependence": consistent,
            "heterogeneous_useful_dependence": heterogeneous,
            "measured_factor_sensitivity": bool(qualifying),
            "consistent_and_heterogeneous": consistent and heterogeneous,
            "qualifying_d_factors_or_interaction": qualifying,
        },
        "limitations": "descriptive correlated cells, shared data and controls; no significance "
        "test, confidence interval, independence claim, or change to P1 promotion",
    }
