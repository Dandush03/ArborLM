"""Paired duration summaries for the registered P3 endpoint and midpoint."""

import math
from typing import Any

from .p2_analysis import _distribution, decompose
from .p2_config import ADDITIVE_ATOL, CONDITIONS, CONTROL, Cell, cells
from .p3_config import DURATIONS, END, MID, START, THRESHOLD


def _directions(changes: list[float]) -> dict[str, int]:
    return {
        "improved": sum(value < 0 for value in changes),
        "worsened": sum(value > 0 for value in changes),
        "unchanged": sum(value == 0 for value in changes),
    }


def describe(rows: list[dict[str, Any]]) -> dict[str, Any]:
    mapped: dict[Cell, dict[str, Any]] = {}
    for row in rows:
        cell = Cell(row["backbone"], row["memory"], row["order"], row["condition"])
        if cell in mapped or set(row["durations"]) != {str(step) for step in DURATIONS}:
            raise ValueError("P3 analysis requires exactly three durations per unique cell")
        required = {"enabled"} if cell.condition == CONTROL else set(CONDITIONS)
        if any(
            set(nlls) != required or not all(math.isfinite(nll) for nll in nlls.values())
            for nlls in row["durations"].values()
        ):
            raise ValueError("missing or non-finite P3 condition NLL")
        mapped[cell] = row["durations"]
    if set(mapped) != set(cells()):
        raise ValueError("P3 analysis requires all 36 registered cells")
    control_cells = [cell for cell in cells() if cell.condition == CONTROL]
    controls = {(cell.backbone, cell.order): mapped[cell] for cell in control_cells}
    learned, control_rows = [], []
    for cell in control_cells:
        raw = mapped[cell]
        start = raw[str(START)]["enabled"]
        control_rows.append(
            {
                **cell.fields(),
                "durations": raw,
                "enabled_nll_changes": {
                    str(step): raw[str(step)]["enabled"] - start for step in (MID, END)
                },
            }
        )
    for cell in cells():
        if cell.condition == CONTROL:
            continue
        trajectory = {}
        for step in DURATIONS:
            raw = mapped[cell][str(step)]
            control_nll = controls[cell.backbone, cell.order][str(step)]["enabled"]
            d = raw["disabled"] - raw["enabled"]
            p = raw["values_permuted"] - raw["enabled"]
            g = control_nll - raw["enabled"]
            s = control_nll - raw["disabled"]
            if not math.isclose(g, d + s, rel_tol=0, abs_tol=ADDITIVE_ATOL):
                raise ValueError("P3 additive identity G = D + S failed")
            trajectory[str(step)] = {**raw, "control": control_nll, "D": d, "P": p, "G": g, "S": s}
        start_values = trajectory[str(START)]
        learned.append(
            {
                **cell.fields(),
                "durations": trajectory,
                "changes_from_256": {
                    str(step): {
                        key: trajectory[str(step)][key] - start_values[key]
                        for key in ("D", "P", "G", "S", "enabled")
                    }
                    for step in (MID, END)
                },
            }
        )
    by_duration: dict[str, Any] = {}
    for step in DURATIONS:
        key = str(step)
        by_duration[key] = {
            "learned_paired_metrics": {
                field: _distribution([row["durations"][key][field] for row in learned])
                for field in ("D", "P", "G", "S", *CONDITIONS)
            },
            "unique_control_nll": _distribution(
                [row["durations"][key]["enabled"] for row in control_rows]
            ),
        }
    changes: dict[str, Any] = {}
    for step in (MID, END):
        key = str(step)
        items = [{**row, **row["changes_from_256"][key]} for row in learned]
        controls_changes = [row["enabled_nll_changes"][key] for row in control_rows]
        changes[key] = {
            "learned": {
                field: _distribution([row[field] for row in items])
                for field in ("D", "P", "G", "S", "enabled")
            },
            "unique_control": _distribution(controls_changes),
            "learned_quality_directions": _directions([row["enabled"] for row in items]),
            "control_quality_directions": _directions(controls_changes),
            "both_delta_d_and_p_positive": sum(row["D"] > 0 and row["P"] > 0 for row in items),
            "factor_decomposition": {metric: decompose(items, metric) for metric in ("D", "G")},
        }
    endpoint = str(END)
    means = by_duration[endpoint]["learned_paired_metrics"]
    delta = changes[endpoint]["learned"]
    endpoint_positive = sum(
        row["durations"][endpoint]["D"] > 0 and row["durations"][endpoint]["P"] > 0
        for row in learned
    )
    criteria = {
        "mean_delta_D_at_threshold": delta["D"]["mean"] >= THRESHOLD,
        "mean_delta_P_at_threshold": delta["P"]["mean"] >= THRESHOLD,
        "delta_joint_positive_at_least_22": changes[endpoint]["both_delta_d_and_p_positive"] >= 22,
        "mean_endpoint_D_at_threshold": means["D"]["mean"] >= THRESHOLD,
        "mean_endpoint_P_at_threshold": means["P"]["mean"] >= THRESHOLD,
        "endpoint_joint_positive_at_least_22": endpoint_positive >= 22,
        "endpoint_enabled_mean_strictly_improved": means["enabled"]["mean"]
        < by_duration[str(START)]["learned_paired_metrics"]["enabled"]["mean"],
        "endpoint_mean_G_nonnegative": means["G"]["mean"] >= 0,
    }
    keys = list(criteria)
    flags = {
        "duration_increases_dependence": all(criteria[key] for key in keys[:3]),
        "endpoint_dependence": all(criteria[key] for key in keys[3:6]),
        "endpoint_quality_guard": all(criteria[key] for key in keys[6:]),
    }
    return {
        "primary_duration": END,
        "secondary_duration": MID,
        "learned_cells": learned,
        "unique_controls": control_rows,
        "by_duration": by_duration,
        "changes_from_256": changes,
        "endpoint_both_d_and_p_positive": endpoint_positive,
        "criteria": criteria,
        "flags": flags,
        "all_three_flags": all(flags.values()),
        "parent_promotion_gate": "failed_unchanged",
        "limitations": "correlated cells, shared controls, repeated trajectory durations and "
        "same-corpus panel; no significance or scaling claim",
    }
