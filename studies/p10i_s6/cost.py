# ruff: noqa: E501
"""P10IS6 cost projection (ADR-0031 sections 16, 17, 18): computed BY CODE from R2's record and the candidate plan's item list. No torch.

R2 times WHOLE PROCESSES through the registered entry point and launch scripts (start-up, imports, per-process input hashing, memory-mapping of the chunk table), one fresh process per probe, and keeps the per-process overhead SEPARATE from the per-unit
rates: ``unit_costs = {"workers", "process_overhead_seconds", "arms": {arm: {"seconds_per_update", "seconds_per_eval": {mode: s}}}, "gates_seconds"}``. A training task is one process (overhead + updates x rate); an evaluation task is one process per training
item (overhead + its evaluations); the gates stage is its measured total. Wall hours = the sum divided by the worker count. The caps formula is ``plan.caps_from_projection`` (charged + 2 x projected remaining), shared by the candidate plan, the freeze and
the caps command. Seconds per update are descriptive cost records of this implementation on this machine, never an efficiency result.
"""

from collections.abc import Mapping, Sequence
from typing import Any

from . import core


def unit_costs_from_probes(overhead: Mapping[str, float], probes: Sequence[Mapping[str, Any]], workers: int, gates_seconds: float) -> dict[str, Any]:
    """``overhead`` is the whole-process time of a probe that does no work (start-up and input checking); ``probes`` are whole-process records of ``train`` and ``eval`` probes of each arm run by ``workers`` processes at once, each with ``seconds`` (whole
    process), ``updates`` or ``evals`` (a mode -> count map). The per-unit rate is (whole seconds - overhead) / units, averaged over the probes."""
    ov = float(overhead["seconds"])
    arms: dict[str, dict[str, Any]] = {}
    for arm in core.ARMS:
        tr = [p for p in probes if p["arm"] == arm and p["kind"] == "train"]
        ev = [p for p in probes if p["arm"] == arm and p["kind"] == "eval"]
        if not tr or not ev:
            raise ValueError(f"no probes of {arm}")
        spu = sum((float(p["seconds"]) - ov) / int(p["updates"]) for p in tr) / len(tr)
        per_eval: dict[str, float] = {}
        for mode in core.MODES:
            vals = [(float(p["seconds"]) - ov) / int(p["evals"][mode]) for p in ev if int(p["evals"].get(mode, 0)) > 0 and len([m for m, n in p["evals"].items() if n]) == 1]
            if vals:
                per_eval[mode] = sum(vals) / len(vals)
        arms[arm] = {"seconds_per_update": spu, "seconds_per_eval": per_eval}
    return {"workers": workers, "process_overhead_seconds": ov, "arms": arms, "gates_seconds": float(gates_seconds)}


def project_hours(plan_items: Mapping[str, Sequence[Mapping[str, Any]]], unit: Mapping[str, Any]) -> dict[str, float]:
    """Wall hours of the registered run from its items and the measured unit costs."""
    k = int(unit["workers"])
    ov = float(unit["process_overhead_seconds"])
    arms = unit["arms"]
    train = sum(ov + int(i["max_update"]) * float(arms[i["arm"]]["seconds_per_update"]) for i in plan_items["train"])
    by_train: dict[str, float] = {}
    for e in plan_items["eval"]:
        per = arms[e["arm"]]["seconds_per_eval"]
        if e["controls"] not in per:
            raise ValueError(f"R2 measured no {e['controls']} evaluation of {e['arm']}")
        by_train[e["train"]] = by_train.get(e["train"], 0.0) + float(per[e["controls"]]) + float(per.get("enabled", 0.0))  # the replay is one more enabled-cost evaluation
    ev = sum(ov + s for s in by_train.values())
    gates = float(unit["gates_seconds"])
    total = train + ev + gates
    return {"hours": total / k / 3600.0, "train_hours": train / k / 3600.0, "eval_hours": ev / k / 3600.0, "gates_hours": gates / k / 3600.0, "workers": float(k), "overhead_hours": (ov * (len(plan_items["train"]) + len(by_train))) / k / 3600.0}
