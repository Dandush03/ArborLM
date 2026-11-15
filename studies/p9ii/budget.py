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
NOT_RUN_MEMORY = "NOT RUN — BUDGET (MEMORY)"
STAGE_SLOTS = core.STAGE_SLOTS
CAP_FLOOR_SECONDS = 60.0  # the floor of the caps of stages that are not rehearsed at real size (gates, analysis, report); stated, not measured


class CapMissing(ValueError):
    """The frozen cap table has no entry for a stage or a configuration: the stage refuses."""
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
    """Measured rehearsal rates of one (arm, size, phase). ``task_overhead_seconds`` is the pool task's wall seconds minus the timed training and evaluation (process
    start-up, data generation, backbone loading), measured in the rehearsal and paid again by every registered task (audit B1). The peaks are those of the training, of the
    evaluation and of the pool's task (M2)."""

    seconds_per_update: float
    peak_rss_bytes: int
    sampled_rss_bytes: int
    evaluation_seconds: float
    task_overhead_seconds: float = 0.0
    evaluation_peak_rss_bytes: int = 0
    task_peak_rss_bytes: int = 0


Rates = dict[Item, Rate]


def rates_from_records(train: Sequence[Mapping[str, Any]], evaluation: Sequence[Mapping[str, Any]], tasks: Mapping[str, Mapping[str, float]] | None = None) -> Rates:
    """Rates from the rehearsal's whitelisted records: ``train`` the ``rehearsal.json`` records, ``evaluation`` the ``rehearsal_evaluate.json`` records (matched by
    label), ``tasks`` the pool's per-task ``{label: {"seconds", "peak_rss_bytes"}}`` of the rehearse stage manifest, keyed by the item label (``item_label``). The task
    overhead is the task's seconds minus the training and evaluation seconds; it is never negative."""
    eval_by_label = {str(r["label"]): r for r in evaluation}
    out: Rates = {}
    for r in train:
        item = (str(r["arm"]), int(r["slots"]), str(r["phase"]))
        e = eval_by_label.get(str(r["label"]))
        e_seconds = float(e["evaluation_wall_seconds"]) if e is not None else math.nan
        task = (tasks or {}).get(item_label(item))
        overhead = max(0.0, float(task["seconds"]) - float(r["wall_seconds"]) - e_seconds) if task is not None and math.isfinite(e_seconds) else 0.0
        out[item] = Rate(
            float(r["seconds_per_update"]), int(r["peak_rss_bytes"]), int(r["sampled_rss_bytes"]), e_seconds, overhead,
            int(e["peak_rss_bytes"]) if e is not None else 0, int(task["peak_rss_bytes"]) if task is not None else 0,
        )  # fmt: skip
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
    overhead = rates[(arm, slots, phases_of(arm)[-1])].task_overhead_seconds
    if arm == "A2":
        pre = min(total, int(sched.u_pre or 0))
        return pre * _rate(rates, arm, slots, "pre") + (total - pre) * _rate(rates, arm, slots, "post") + overhead
    if arm == "A4":
        anneal = min(total, int(sched.t_anneal or 0))
        return anneal * max(_rate(rates, arm, slots, "k0"), _rate(rates, arm, slots, "mid")) + (total - anneal) * _rate(rates, arm, slots, "k8") + overhead
    return total * _rate(rates, arm, slots, "main") + overhead


def cell_evaluation_seconds(arm: str, slots: int, stage: int, rates: Rates) -> float:
    """One measured full evaluation per readout (two at Stage 2), plus the task overhead of the evaluation process (audit B1); the evaluation of A2 and A4 is the one of
    their last rehearsed phase (the evaluation does not depend on the phase)."""
    rate = rates[(arm, slots, phases_of(arm)[-1])]
    return len(core.stage_readouts(stage)) * rate.evaluation_seconds + rate.task_overhead_seconds


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


def peak_of(rate: Rate) -> int:
    return max(rate.peak_rss_bytes, rate.sampled_rss_bytes, rate.evaluation_peak_rss_bytes, rate.task_peak_rss_bytes)


def memory_headroom(rates: Rates, slots: int | None = None) -> dict[str, Any]:
    """The rehearsal must show 2x headroom on memory: twice the largest peak resident size within 3 GiB per worker, and six workers at twice that within 24 GiB. The
    peak is the largest of the training peak, the sampled peak, the evaluation peak and the pool task's peak (M2); ``slots`` restricts it to one size (a stage's own).
    ``status`` is NOT RUN — BUDGET (MEMORY) when the rule fails."""
    peak = max((peak_of(r) for (arm, n, phase), r in rates.items() if slots in (None, n)), default=0)
    per_worker = core.HEADROOM * peak <= core.RSS_WORKER_BYTES
    aggregate = core.HEADROOM * peak * core.WORKERS <= core.RSS_AGGREGATE_BYTES
    ok = bool(per_worker and aggregate)
    return {"slots": slots, "peak_rss_bytes": peak, "per_worker_ok": per_worker, "aggregate_ok": aggregate, "ok": ok, "status": None if ok else NOT_RUN_MEMORY}


def memory_by_stage(rates: Rates) -> dict[str, dict[str, Any]]:
    """The memory rule of every stage at its own size (Stage 1: 4,096 slots, Stage 2: 16,384, Stage 3: 65,536)."""
    return {f"stage{st}": memory_headroom(rates, n) for st, n in STAGE_SLOTS.items()}


def caps_table(
    rates: Rates,
    hyper: core.Hyper,
    *,
    gates_wall_seconds: float,
    analysis_wall_seconds: float,
    report_wall_seconds: float,
    unit: int = core.UPDATES,
    floor_seconds: float = CAP_FLOOR_SECONDS,
) -> dict[str, Any]:
    """The frozen cap table (``studies/p9ii/freeze/stage_caps.json``), one source of truth: each cap is twice the rehearsed projection (task overhead included) of
    what it bounds. Stage 1 has a training and an evaluation cap; Stage 2 one entry per possible configuration and Stage 3 one per selected arm, so a stage's cap is
    that of the configuration its gate selects. Gates, analysis and report are not rehearsed at real size: twice a measured time with a stated floor."""
    def entry(p: Mapping[str, float]) -> dict[str, float]:
        return {"train": core.HEADROOM * float(p["training_seconds"]), "evaluate": core.HEADROOM * float(p["evaluation_seconds"])}

    p1 = stage_projection(core.stage1_cells(), 1, rates, hyper, unit)
    return {
        "rule": "each cap = 2 x the rehearsed projection (task overhead included); gates, analysis and report: 2 x a measured time with the stated floor",
        "floor_seconds": floor_seconds,
        "gates": max(floor_seconds, core.HEADROOM * gates_wall_seconds),
        "stage1": entry(p1._asdict()),
        "stage2": {k: entry(v) for k, v in stage2_projection_table(rates, hyper, unit).items()},
        "stage3": {k: entry(v) for k, v in stage3_projection_table(rates, hyper, unit).items()},
        "analysis": max(floor_seconds, core.HEADROOM * analysis_wall_seconds),
        "report": max(floor_seconds, core.HEADROOM * report_wall_seconds),
    }


def cap_for(table: Mapping[str, Any], stage: str, key: str | None = None) -> dict[str, float] | float:
    """The cap of ``stage`` (``gates``, ``stage1``, ``stage2``, ``stage3``, ``analysis``, ``report``); ``key`` is the configuration (``config_key``) of Stage 2 or the
    selected arm of Stage 3. A stage or configuration with no entry raises ``CapMissing`` (the stage refuses)."""
    if stage not in table:
        raise CapMissing(f"the frozen cap table has no entry for {stage!r}")
    value = table[stage]
    if stage in ("stage2", "stage3"):
        if key is None or key not in value:
            raise CapMissing(f"the frozen cap table has no entry for {stage} {key!r}")
        value = value[key]
    return value  # type: ignore[no-any-return]


def cost_differences(rates: Rates) -> dict[str, dict[str, float]]:
    """Measured wall seconds per update that one mechanism adds (descriptive, section 8.2 cost): L_addr (A1 - A0), L_div (A5-D - A0), A4's wide read at k_0 and at the
    midpoint of its schedule (against its k = 8 phase) and A2's phase 1 against phase 2, per size where both were rehearsed. No efficiency claim."""
    pairs = {"L_addr (A1 - A0)": (("A1", "main"), ("A0", "main")), "L_div (A5-D - A0)": (("A5-D", "main"), ("A0", "main")), "A4 read at k_0 (k0 - k8)": (("A4", "k0"), ("A4", "k8")), "A4 read at the midpoint (mid - k8)": (("A4", "mid"), ("A4", "k8")), "A2 phase 1 (pre - post)": (("A2", "pre"), ("A2", "post"))}
    out: dict[str, dict[str, float]] = {}
    for name, ((a, pa), (b, pb)) in pairs.items():
        for n in core.SLOTS_BY_SIZE:
            if (a, n, pa) in rates and (b, n, pb) in rates:
                out.setdefault(name, {})[str(n)] = rates[(a, n, pa)].seconds_per_update - rates[(b, n, pb)].seconds_per_update
    return out


def stage1_budget(rates: Rates, hyper: core.Hyper, remaining_a_seconds: float, unit: int = core.UPDATES) -> tuple[Projection, BudgetDecision]:
    p = stage_projection(core.stage1_cells(), 1, rates, hyper, unit)
    return p, budget_decision(p.total_seconds, remaining_a_seconds)


def stage2_decision(advancing: Sequence[str], table: Mapping[str, Mapping[str, float]], remaining_b_seconds: float) -> BudgetDecision:
    """Read the frozen table for the configuration the gate selected and decide against Budget B."""
    return budget_decision(float(table[config_key(advancing)]["total_seconds"]), remaining_b_seconds)


def stage3_decision(selected: str, table: Mapping[str, Mapping[str, float]], remaining_b_seconds: float) -> BudgetDecision:
    """Stage 3 needs twice its projection within what remains of Budget B after the time Stage 2 actually charged (the caller passes the ledger's remainder)."""
    return budget_decision(float(table[selected]["total_seconds"]), remaining_b_seconds)
