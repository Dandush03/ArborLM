# ruff: noqa: E501
"""P9II budgets and projections (ADR-0019 section 10): the rehearsal matrix (every distinct (arm, size, phase)), the rates a rehearsal measures, the
projection of a stage from them (measured seconds per update x planned updates, A4's annealing phase at its most expensive measured rate, plus the measured
evaluation, arranged in rounds of six), the table of every possible Stage 2 configuration, the 2x headroom rule and the NOT RUN — BUDGET outcome.
Everything here is a pure function of its inputs; every number it returns is analytical (a projection from measured rates), never a measurement of a
result, and none is an efficiency claim.
"""

import itertools
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, NamedTuple

from . import core

Item = tuple[str, int, str]  # (arm, slots, phase)
NOT_RUN_BUDGET = "NOT RUN — BUDGET"
PHASES: dict[str, tuple[str, ...]] = {"A2": ("pre", "post"), "A4": ("k0", "mid", "k8")}
NEVER_AT_65536 = ("A2", "A4", "A1-S")  # section 10: not rehearsed where they never run


def phases_of(arm: str) -> tuple[str, ...]:
    return PHASES.get(arm, ("main",))


def rehearsal_items() -> list[Item]:
    """Every distinct (arm, size, phase) of the matrix: the nine arms at the three sizes, A2 before and after its switch, A4 at k_0, at the midpoint of its
    schedule and at k = 8; A2, A4 and A1-S are not rehearsed at 65,536."""
    return [(arm, slots, phase) for arm in core.ARMS for slots in core.SLOTS_BY_SIZE if not (slots == 65536 and arm in NEVER_AT_65536) for phase in phases_of(arm)]


def item_label(item: Item) -> str:
    arm, slots, phase = item
    return f"REH-{arm}-n{slots}-{phase}"


@dataclass(frozen=True)
class Rate:
    seconds_per_update: float
    peak_rss_bytes: int
    sampled_rss_bytes: int
    evaluation_seconds: float


Rates = dict[Item, Rate]


def rates_from_records(train: Sequence[Mapping[str, Any]], evaluation: Sequence[Mapping[str, Any]]) -> Rates:
    """Rates from the rehearsal's whitelisted records: ``train`` the ``rehearsal.json`` records, ``evaluation`` the ``rehearsal_evaluate.json`` records, matched
    by label."""
    evaluation_by_label = {str(r["label"]): float(r["evaluation_wall_seconds"]) for r in evaluation}
    out: Rates = {}
    for r in train:
        item = (str(r["arm"]), int(r["slots"]), str(r["phase"]))
        out[item] = Rate(float(r["seconds_per_update"]), int(r["peak_rss_bytes"]), int(r["sampled_rss_bytes"]), evaluation_by_label.get(str(r["label"]), math.nan))
    return out


def missing_items(rates: Rates) -> list[Item]:
    return [i for i in rehearsal_items() if i not in rates or not math.isfinite(rates[i].evaluation_seconds)]


def _rate(rates: Rates, arm: str, slots: int, phase: str) -> float:
    return rates[(arm, slots, phase)].seconds_per_update


def cell_training_seconds(arm: str, slots: int, stage: int, rates: Rates, hyper: core.Hyper, unit: int = core.UPDATES) -> float:
    """Measured seconds per update x the cell's planned updates. A2: its phase 1 at the 'pre' rate and the rest at 'post'. A4: the annealing phase at the more
    expensive of the measured k_0 and midpoint rates, the rest at the k = 8 rate."""
    total = core.stage_updates(stage, unit)
    sched = core.schedule_for(arm, stage, hyper, slots, unit)
    if arm == "A2":
        pre = min(total, int(sched.u_pre or 0))
        return pre * _rate(rates, arm, slots, "pre") + (total - pre) * _rate(rates, arm, slots, "post")
    if arm == "A4":
        anneal = min(total, int(sched.t_anneal or 0))
        return anneal * max(_rate(rates, arm, slots, "k0"), _rate(rates, arm, slots, "mid")) + (total - anneal) * _rate(rates, arm, slots, "k8")
    return total * _rate(rates, arm, slots, "main")


def cell_evaluation_seconds(arm: str, slots: int, stage: int, rates: Rates) -> float:
    """One measured full evaluation per readout (two at Stage 2); the evaluation of A2 and A4 is the one of their last rehearsed phase (the evaluation does not depend on the phase)."""
    phase = phases_of(arm)[-1]
    return len(core.stage_readouts(stage)) * rates[(arm, slots, phase)].evaluation_seconds


def makespan(seconds: Sequence[float], workers: int = core.WORKERS) -> float:
    """Rounds of ``workers`` cells: the cells sorted by decreasing time, each round as long as its longest cell."""
    ordered = sorted(seconds, reverse=True)
    return float(sum(ordered[i] for i in range(0, len(ordered), workers)))


class Projection(NamedTuple):
    cells: int
    training_seconds: float
    evaluation_seconds: float
    total_seconds: float
    rounds: int


def stage_projection(cells: Sequence[core.Cell], stage: int, rates: Rates, hyper: core.Hyper, unit: int = core.UPDATES, workers: int = core.WORKERS) -> Projection:
    """Training makespan plus evaluation makespan of a stage's cells, in rounds of ``workers`` (analytical, from measured rates)."""
    train = makespan([cell_training_seconds(c.arm, c.slots, stage, rates, hyper, unit) for c in cells], workers)
    ev = makespan([cell_evaluation_seconds(c.arm, c.slots, stage, rates) for c in cells], workers)
    return Projection(len(cells), train, ev, train + ev, math.ceil(len(cells) / workers))


def stage2_configurations() -> list[tuple[str, ...]]:
    """Every possible Stage 2 configuration: A0 alone, A0 and one advancing arm, A0 and two (in the order of the gate): 1 + 5 + 10."""
    order = core.ADVANCE_ORDER
    return [(), *[(a,) for a in order], *itertools.combinations(order, 2)]


def config_key(advancing: Sequence[str]) -> str:
    return "+".join(advancing) if advancing else "A0-only"


def stage2_projection_table(rates: Rates, hyper: core.Hyper, unit: int = core.UPDATES) -> dict[str, dict[str, float]]:
    """The projection of every possible Stage 2 configuration (recorded at the freeze, so the Stage 1 gate reads a table and computes nothing new)."""
    out: dict[str, dict[str, float]] = {}
    for advancing in stage2_configurations():
        p = stage_projection(core.stage2_cells(advancing), 2, rates, hyper, unit)
        out[config_key(advancing)] = {"cells": p.cells, "training_seconds": p.training_seconds, "evaluation_seconds": p.evaluation_seconds, "total_seconds": p.total_seconds, "rounds": p.rounds}
    return out


def stage3_projection_table(rates: Rates, hyper: core.Hyper, unit: int = core.UPDATES) -> dict[str, dict[str, float]]:
    """The projection of Stage 3 for every constant-objective selected arm (A0, A1, A5-C, A5-D)."""
    out: dict[str, dict[str, float]] = {}
    for selected in ("A0", "A1", "A5-C", "A5-D"):
        p = stage_projection(core.stage3_cells(selected), 3, rates, hyper, unit)
        out[selected] = {"cells": p.cells, "training_seconds": p.training_seconds, "evaluation_seconds": p.evaluation_seconds, "total_seconds": p.total_seconds, "rounds": p.rounds}
    return out


class BudgetDecision(NamedTuple):
    run: bool
    status: str | None  # None when it runs, else NOT RUN — BUDGET
    projection_seconds: float
    required_seconds: float  # twice the projection
    remaining_seconds: float
    stage_cap_seconds: float


def budget_decision(projection_seconds: float, remaining_seconds: float) -> BudgetDecision:
    """Section 10: a stage starts only if twice its rehearsed projection is within what remains of its budget. If it is not, nothing registered is run and the
    status is NOT RUN — BUDGET (no reduced stage exists: no draw, arm or update is dropped to make it fit). The stage's time cap is twice its projection."""
    required = core.HEADROOM * projection_seconds
    fits = math.isfinite(projection_seconds) and required <= remaining_seconds
    return BudgetDecision(fits, None if fits else NOT_RUN_BUDGET, projection_seconds, required, remaining_seconds, required)


def memory_headroom(rates: Rates) -> dict[str, Any]:
    """The rehearsal must show 2x headroom on memory: twice the largest peak resident size within 3 GiB per worker, and six workers at twice that within 24 GiB."""
    peak = max((max(r.peak_rss_bytes, r.sampled_rss_bytes) for r in rates.values()), default=0)
    per_worker = core.HEADROOM * peak <= core.RSS_WORKER_BYTES
    aggregate = core.HEADROOM * peak * core.WORKERS <= core.RSS_AGGREGATE_BYTES
    return {"peak_rss_bytes": peak, "per_worker_ok": per_worker, "aggregate_ok": aggregate, "ok": bool(per_worker and aggregate)}


def stage1_budget(rates: Rates, hyper: core.Hyper, remaining_a_seconds: float, unit: int = core.UPDATES) -> tuple[Projection, BudgetDecision]:
    p = stage_projection(core.stage1_cells(), 1, rates, hyper, unit)
    return p, budget_decision(p.total_seconds, remaining_a_seconds)


def stage2_decision(advancing: Sequence[str], table: Mapping[str, Mapping[str, float]], remaining_b_seconds: float) -> BudgetDecision:
    """Read the frozen table for the configuration the gate selected and decide against Budget B."""
    return budget_decision(float(table[config_key(advancing)]["total_seconds"]), remaining_b_seconds)


def stage3_decision(selected: str, table: Mapping[str, Mapping[str, float]], remaining_b_seconds: float) -> BudgetDecision:
    """Stage 3 needs twice its projection within what remains of Budget B after the time Stage 2 actually charged (the caller passes the ledger's remainder)."""
    return budget_decision(float(table[selected]["total_seconds"]), remaining_b_seconds)
