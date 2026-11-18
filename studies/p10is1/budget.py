# ruff: noqa: E501
"""P10IS1 block budget and projection (ADR-0024 sections 15 and 17.1): the frozen projection code. A design ceiling with a written rule: block M's hour caps sum to at most 60 charged hours, so the projected charged
time at 1x (the hours already charged, H_c, plus the projection of everything still to run) is at most B = (60 + H_c) / 2. Ladder levels are granted to WHOLE cells (all arms, all five replicates, costed as if every
replicate used the level) in a fixed order of levels (j = 1..4, all cells at level j before any at level j + 1) and of cells (ascending load, then ascending facts: 2K/256, 8K/1K, 32K/4K); a level is granted only if the whole
cell at that level fits; a cell whose next level would exceed B is closed and gets no later level. A base plan above B is REFUSED by the freeze. The projected charged time of a stage is the makespan of a longest-
processing-time-first schedule of its items on the stage's worker count and never less than its longest item. Inputs: the measuring rehearsal's rates only (seconds per update per arm and size, evaluation seconds
per snapshot, the contention ratio) and the ledger of hours already charged; no registered result. All numbers here are projections (hypothetical until measured), never measured efficiency.
"""

import heapq
import math
from collections.abc import Mapping, Sequence
from typing import Any

from . import core

BASE_PLAN_ABOVE_BUDGET = "BASE PLAN ABOVE BUDGET"


def budget_hours(h_charged: float, cfg: Mapping[str, Any] | None = None) -> float:
    """B = (60 + H_c) / 2: the projected charged time at 1x, so that the caps (charged + 2 x projected remaining) sum to at most 60."""
    total = float(core.cfg_of(cfg)["budget"]["total_cap_hours"])
    return (total + h_charged) / 2.0


def makespan(seconds: Sequence[float], workers: int) -> float:
    """The makespan of a longest-processing-time-first schedule of ``seconds`` on ``workers`` workers; never less than the longest item (charged time is a stage's wall time)."""
    if workers < 1:
        raise ValueError("at least one worker")
    if not seconds:
        return 0.0
    loads = [0.0] * min(workers, len(seconds))
    heapq.heapify(loads)
    for s in sorted(seconds, reverse=True):
        heapq.heappush(loads, heapq.heappop(loads) + float(s))
    return max(max(loads), max(seconds))


class Rates:
    """The measuring rehearsal's rates: ``train[(arm, slots)]`` seconds per update (single process), ``evaluate[(arm, slots)]`` seconds per snapshot evaluation (DEP at every snapshot included), ``contention`` the
    ratio of seconds per update at the worker count to the isolated figure, ``fixed`` seconds of the stages that are not training or evaluation (gates, timing, throughput, analysis, report, counting rehearsal)."""

    def __init__(self, train: Mapping[tuple[str, int], float], evaluate: Mapping[tuple[str, int], float], contention: float, fixed: Mapping[str, float], workers: int) -> None:
        if contention < 1.0 or not math.isfinite(contention):
            raise ValueError("the contention ratio is at least 1")
        self.train, self.evaluate, self.contention, self.fixed, self.workers = dict(train), dict(evaluate), float(contention), dict(fixed), int(workers)

    def update_seconds(self, arm: str, slots: int) -> float:
        return self.train[(arm, slots)] * self.contention

    def snapshot_seconds(self, arm: str, slots: int) -> float:
        return self.evaluate[(arm, slots)]


def training_items(cells: Sequence[Mapping[str, Any]], lengths: Mapping[str, int], rates: Rates) -> list[float]:
    """One training item per cell: its length x seconds per update x the contention ratio. ``lengths``: label -> updates (the plan's run length; a ladder cell's current grant)."""
    return [lengths[c["label"]] * rates.update_seconds(c["arm"], c["slots"]) for c in cells]


def evaluation_items(cells: Sequence[Mapping[str, Any]], lengths: Mapping[str, int], rates: Rates) -> list[float]:
    """One evaluation item per cell: the snapshots at or below its length x evaluation seconds per snapshot (F-OQ cells carry the index read in that figure)."""
    return [sum(1 for u in c["snapshots"] if u <= lengths[c["label"]]) * rates.snapshot_seconds(c["arm"], c["slots"]) for c in cells]


def project(cells: Sequence[Mapping[str, Any]], grants: Mapping[str, int], rates: Rates) -> dict[str, Any]:
    """The projected charged seconds of every stage that depends on the lengths, with a ladder cell at its current grant (``grants``: cell name -> G; U0 for a base plan) and every other cell at its run length:
    training and evaluation, each a makespan on the worker count, plus the fixed stages."""
    lengths = {c["label"]: (int(grants[core.cell_name(c["facts"], c["slots"])]) if c["ladder_cell"] else int(c["run"])) for c in cells}
    tr, ev = training_items(cells, lengths, rates), evaluation_items(cells, lengths, rates)
    train_s, eval_s = makespan(tr, rates.workers), makespan(ev, rates.workers)
    # the COUNTING REHEARSAL (section 17.1 names it): every stage of ONE replicate on the rehearsal draw at the same lengths (a ladder cell at its granted length, as if it never stopped early), training then evaluation
    first = min((c["draw"] for c in cells), default=0)
    one = [c for c in cells if c["draw"] == first]
    count_s = makespan(training_items(one, lengths, rates), rates.workers) + makespan(evaluation_items(one, lengths, rates), rates.workers)
    fixed = sum(rates.fixed.values())  # gates, baselines, timing, throughput, analysis, report: whatever the measuring rehearsal measured
    return {
        "train_seconds": train_s, "evaluate_seconds": eval_s, "counting_rehearsal_seconds": count_s, "fixed_seconds": fixed, "remaining_seconds": train_s + eval_s + count_s + fixed,
        "longest_training_item_seconds": max(tr) if tr else 0.0, "workers": rates.workers,
    }  # fmt: skip


def grant_levels(cells: Sequence[Mapping[str, Any]], rates: Rates, h_charged: float, cfg: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """The whole rule of section 17.1: the base plan (every ladder cell at U0), then levels granted to whole cells in the fixed order. Returns the plan block: ``refused`` (BASE PLAN ABOVE BUDGET) or the grants, with
    every level considered, the closed cells and the projection (hours). ``cells`` carry ``ladder_cell`` and ``u0`` for the ladder cells."""
    c = core.cfg_of(cfg)
    b = budget_hours(h_charged, c)
    names = [core.cell_name(*x) for x in core.ladder_cells(c, sat256=any(y["facts"] == 2048 and y["slots"] == 256 for y in cells))]
    u0 = {core.cell_name(x["facts"], x["slots"]): int(x["u0"]) for x in cells if x["ladder_cell"]}
    grants = {n: u0[n] for n in names}

    def total_hours(g: Mapping[str, int]) -> float:
        return h_charged + project(cells, g, rates)["remaining_seconds"] / 3600.0

    base = total_hours(grants)
    out: dict[str, Any] = {"h_charged_hours": h_charged, "budget_B_hours": b, "base_total_hours": base, "workers": rates.workers, "contention": rates.contention, "levels_considered": [], "closed": [], "bound_at_4_u0_printed": {}}
    out["bound_at_4_u0_printed"] = {n: 4 * u0[n] for n in names}  # the projection's assumption for the loaded cells is U0, with the bound at 4 x U0 printed beside it
    if base > b + 1e-9:
        out.update(status=BASE_PLAN_ABOVE_BUDGET, refused=True, grants=grants, total_hours=base, remaining_hours=base - h_charged, longest_item_hours=project(cells, grants, rates)["longest_training_item_seconds"] / 3600.0)
        return out
    closed: set[str] = set()
    for j in range(1, int(c["budget"]["level_count"]) + 1):
        for name in names:
            if name in closed:
                continue
            cand = core.levels_above(u0[name], c)[j - 1]
            trial = {**grants, name: cand}
            t = total_hours(trial)
            granted = t <= b + 1e-9
            out["levels_considered"].append({"level": j, "cell": name, "length": cand, "total_hours_with_it": t, "granted": granted})
            if granted:
                grants = trial
            else:
                closed.add(name)
                out["closed"].append({"cell": name, "at_level": j})
    p = project(cells, grants, rates)
    total = h_charged + p["remaining_seconds"] / 3600.0
    out.update(status="WITHIN BUDGET", refused=False, grants=grants, total_hours=total, remaining_hours=p["remaining_seconds"] / 3600.0, longest_item_hours=p["longest_training_item_seconds"] / 3600.0, stage_hours={"train": p["train_seconds"] / 3600.0, "evaluate": p["evaluate_seconds"] / 3600.0, "counting_rehearsal": p["counting_rehearsal_seconds"] / 3600.0, "fixed": p["fixed_seconds"] / 3600.0})
    return out


def choose_workers(candidates: Mapping[int, Rates], cells: Sequence[Mapping[str, Any]], grants: Mapping[str, int]) -> dict[str, Any]:
    """The worker count with the lower projected charged hours is used (a cost rule, not a scientific choice); ties go to the smaller count."""
    hours = {w: project(cells, grants, r)["remaining_seconds"] / 3600.0 for w, r in candidates.items()}
    best = min(sorted(hours), key=lambda w: (hours[w], w))
    return {"chosen_workers": best, "projected_hours_by_workers": hours}


def caps_from_projection(h_charged: float, stage_hours: Mapping[str, float], cfg: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Section 15: a cap is charged + 2 x projected remaining, rounded up to the hour. The total cap uses the whole projected remaining; each stage cap is twice its projection, rounded up. By construction of B the
    total never exceeds 60; the sum of the rounded stage caps is printed with the total and with the flag 'above 60' (a cap or an extension beyond 60 is the human lead's own decision)."""
    c = core.cfg_of(cfg)
    remaining = sum(stage_hours.values())
    total = core.propose_cap_hours(h_charged, remaining)
    stages = {k: float(math.ceil(2.0 * v - 1e-9)) for k, v in stage_hours.items()}
    limit = float(c["budget"]["total_cap_hours"])
    return {"total_cap_hours": total, "stage_cap_hours": stages, "sum_of_stage_caps_plus_charged": sum(stages.values()) + h_charged, "total_above_limit": total > limit + 1e-9, "limit_hours": limit}
