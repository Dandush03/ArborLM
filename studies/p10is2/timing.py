# ruff: noqa: E501
"""The timing benchmark's control logic (ADR-0025 section 10, "Timing benchmark (stage 7)"; ruling G22). Descriptive: no wall-time comparison and no label is registered on it.

It runs ALONE: it is opened only when no process of this or any other study is alive on the machine, and that is checked again with the quiet condition before each repetition. The quiet condition is read
BEFORE each repetition starts, never at its end: the 1-minute load average must be at most 2.0 after at least 60 seconds with no study process running. The 30-minute bound applies to each repetition's start,
counted from the opening of the attempt. If a repetition cannot start within it, the attempt ends, its completed repetitions are kept and marked INCOMPLETE ATTEMPT, and the stage is rescheduled. The first
attempt with three completed repetitions is the record; no attempt is chosen on its figures. After five attempts without one the lead records NOT MEASURED and the stage is closed. Every wait is bounded.
The load measured before and after each repetition is printed with every figure; a set of repetitions whose coefficient of variation exceeds 5% is marked UNSTABLE.

The clock, the sleep, the load reading and the process listing are injected, so this module measures nothing itself and its tests never sleep.
"""

import statistics
from collections.abc import Callable, Mapping, Sequence
from typing import Any


def quiet(load1: float, alive: Sequence[str], quiet_seconds: float, cfg: Mapping[str, Any]) -> bool:
    t = cfg["timing"]
    return load1 <= float(t["quiet_load_max"]) and not alive and quiet_seconds >= float(t["quiet_wait_seconds"])


def cv(values: Sequence[float]) -> float:
    """Coefficient of variation (population standard deviation over the mean) of the repetitions' durations."""
    m = statistics.fmean(values)
    return 0.0 if m == 0 else statistics.pstdev(values) / m


def run_attempt(
    repetition: Callable[[], float], *, cfg: Mapping[str, Any], clock: Callable[[], float], sleep: Callable[[float], None], load_fn: Callable[[], float], alive_fn: Callable[[], Sequence[str]], poll_seconds: float = 5.0
) -> dict[str, Any]:  # fmt: skip
    """One attempt: up to ``repetitions`` repetitions, each started only when the quiet condition holds (read before it starts), each start within ``start_bound_minutes`` of the attempt's opening. ``repetition()``
    runs the benchmark once and returns its duration. A repetition that cannot start within the bound ends the attempt: INCOMPLETE ATTEMPT, completed repetitions kept."""
    t = cfg["timing"]
    opened = clock()
    bound = float(t["start_bound_minutes"]) * 60.0
    need = int(t["repetitions"])
    reps: list[dict[str, Any]] = []
    quiet_since: float | None = None
    while len(reps) < need:
        now = clock()
        if now - opened > bound:
            return {"status": "INCOMPLETE ATTEMPT", "repetitions": reps, "reason": f"repetition {len(reps) + 1} could not start within {t['start_bound_minutes']} minutes of the attempt's opening"}
        alive = list(alive_fn())
        load = load_fn()
        if alive or load > float(t["quiet_load_max"]):
            quiet_since = None
        elif quiet_since is None:
            quiet_since = now
        if quiet_since is not None and quiet(load, alive, now - quiet_since, cfg):
            before = {"load1": load, "alive": alive, "quiet_seconds": now - quiet_since}
            dur = float(repetition())
            reps.append({"seconds": dur, "load_before": before, "load_after": load_fn(), "alive_after": list(alive_fn())})
            quiet_since = None  # the quiet condition is checked again before the next repetition
            continue
        sleep(poll_seconds)
    d = [r["seconds"] for r in reps]
    return {"status": "COMPLETE", "repetitions": reps, "median_seconds": statistics.median(d), "cv": cv(d), "unstable": cv(d) > float(t["unstable_cv"])}


def stage_record(attempts: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]) -> dict[str, Any]:
    """The first attempt with three completed repetitions is the record (never chosen on its figures); incomplete attempts keep their repetitions marked INCOMPLETE ATTEMPT; after five attempts without a
    record the stage needs the lead's decision NOT MEASURED."""
    for i, a in enumerate(attempts):
        if a["status"] == "COMPLETE":
            return {"status": "MEASURED", "attempt": i + 1, "record": a, "unstable": a["unstable"], "incomplete_attempts_kept": [x for x in attempts[:i]]}
    if len(attempts) >= int(cfg["timing"]["max_attempts"]):
        return {"status": "NEEDS DECISION: NOT MEASURED", "attempts": len(attempts), "note": "the lead records NOT MEASURED and the stage is closed"}
    return {"status": "RESCHEDULE", "attempts": len(attempts)}
