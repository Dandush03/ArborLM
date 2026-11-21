# ruff: noqa: E501
"""Caps by code (ADR-0025 section 10, item 3), shared by both parts: each registered stage's cap is 2 x its projected time; the part's total cap is the part's charge before its freeze + 2 x the projected time of
ALL its registered stages (the pre-freeze charge counted once, in the total). Projected times come from the part's measuring rehearsal's rates and the plan's counts."""

import math
from collections.abc import Mapping
from typing import Any

from . import core


def project_stage_seconds(units: Mapping[str, float], seconds_per_unit: Mapping[str, float]) -> dict[str, float]:
    """Projected time of each registered stage from the measuring rehearsal's rates and the plan's counts. Part Q's projection assumes both split pools are generated to the end and the whole Q_check reserve is
    drawn. A stage with units and no measured rate is an error: nothing is guessed."""
    out: dict[str, float] = {}
    for stage, n in units.items():
        if stage not in seconds_per_unit:
            raise ValueError(f"no measured rate for stage {stage!r}")
        out[stage] = float(n) * float(seconds_per_unit[stage])
    return out


def caps_proposal(charged_before_freeze_seconds: float, projected: Mapping[str, float]) -> dict[str, Any]:
    """Each registered stage's cap is 2 x its projected time; the part's total cap is the charge before the freeze + 2 x the projected time of all its stages (the pre-freeze charge counted once, in the total).
    Hours, rounded UP to 0.01 h. The lead writes them in the config; the freeze requires the config to equal this proposal."""

    def hours(s: float) -> float:
        return math.ceil(s / 3600.0 * 100.0 - 1e-9) / 100.0

    caps = {f"{k}_hours": hours(core.stage_cap_seconds(v)) for k, v in projected.items()}
    caps["total_hours"] = hours(core.total_cap_seconds(charged_before_freeze_seconds, projected))
    return caps


def caps_match_config(cfg: Mapping[str, Any], proposal: Mapping[str, float]) -> list[str]:
    return [f"stage_caps.{k}: config {cfg['stage_caps'].get(k)!r}, computed {v!r}" for k, v in proposal.items() if abs(float(cfg["stage_caps"].get(k, -1.0)) - float(v)) > 1e-9]


