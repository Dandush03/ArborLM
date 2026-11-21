# ruff: noqa: E501
"""P10IS3 cost projection (ADR-0026 sections 7 and 9; R5): computed BY CODE from R2's record and the candidate plan's item list. The registered cap is ``charged so far + 2 x projected remaining`` (0 charged at candidate
time), never typed. The unit costs of R2 are measured with k workers running at once (the registered worker count), so each already carries the parallel slowdown; the projection divides the summed seconds by k.
Seconds per update are descriptive records of this implementation on this machine, not an efficiency result. No torch."""

from collections.abc import Mapping, Sequence
from typing import Any

from . import core


def unit_costs_from_probes(single: Mapping[str, Mapping[str, float]], parallel: Sequence[Mapping[str, Any]], workers: int) -> dict[str, Any]:
    """``single[arm]`` is the probe of one worker running alone; ``parallel`` is the list of probes of the k workers running together. The k-worker unit cost of an arm is the mean over its probes in the parallel phase."""
    arms: dict[str, dict[str, float]] = {}
    slowdown: dict[str, float] = {}
    for arm in core.ARMS:
        ps = [p for p in parallel if p["arm"] == arm]
        if not ps:
            raise ValueError(f"no parallel probe of {arm}")
        k = {n: sum(float(p[n]) for p in ps) / len(ps) for n in ("seconds_per_update", "seconds_per_enabled_read", "seconds_per_full_read_set")}
        arms[arm] = k
        slowdown[arm] = k["seconds_per_update"] / float(single[arm]["seconds_per_update"])
    return {"workers": workers, "arms": arms, "slowdown": slowdown}


def project_hours(plan_items: Mapping[str, Sequence[Mapping[str, Any]]], unit: Mapping[str, Any], cfg: Mapping[str, Any]) -> dict[str, float]:
    """Wall hours of the registered run from its items and the k-worker unit costs: training (every train item to its ``max_update``), evaluation (full: one full read set; enabled: the enabled read, its replay and the
    disabled read; step 0: enabled and disabled), the gates (a short and a long run per arm-regime for the prefix-identity gate, and BASE on nine parents), divided by the worker count."""
    arms = unit["arms"]
    k = int(unit["workers"])
    train = sum(int(i["max_update"]) * float(arms[i["arm"]]["seconds_per_update"]) for i in plan_items["train"])
    ev = 0.0
    for i in plan_items["eval"]:
        a = arms[i["arm"]]
        ev += float(a["seconds_per_full_read_set"]) if i["controls"] == "full" else (3.0 if i["controls"] == "enabled" else 2.0) * float(a["seconds_per_enabled_read"])
    short, long_ = int(cfg["duration"]["checkpoints"][0]), int(cfg["duration"]["u_star"])
    gates = sum((short + long_) * float(arms[a]["seconds_per_update"]) + 4.0 * float(arms[a]["seconds_per_enabled_read"]) for g in core.REGIMES for a in core.REGIME_ARMS[g])
    gates += 9 * 3 * float(arms[core.TREE]["seconds_per_enabled_read"])
    total = train + ev + gates
    return {"hours": total / k / 3600.0, "train_hours": train / k / 3600.0, "eval_hours": ev / k / 3600.0, "gates_hours": gates / k / 3600.0, "workers": float(k)}
