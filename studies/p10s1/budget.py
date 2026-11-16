# ruff: noqa: E501
"""P10S1 budgets and projections (ADR-0021 section 10, revision 5): the rehearsal matrix (every configuration of the plan at real size), the rates a rehearsal measures (task start-up time
included), the contention ratio c, the projection of every stage, C_need (charged so far plus twice the projected remaining time, training from isolated rates times c, evaluation from rehearsed
seconds per snapshot, longest first on six workers), the cap rule (cap = C_need rounded up to the hour if it is at most C_max; twice the measured peak within the memory caps, evaluation peaks
included), the cuts in their fixed order, and the frozen cap table with one entry per possible configuration.

Everything here is a pure function of its inputs. Every number it returns is analytical (a projection from measured rates), never a measurement of a result, and none is an
efficiency claim. The cap is an argument (the config value ``resources.cap_hours``); this module holds no number of hours.
"""

import dataclasses
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, NamedTuple

from . import core
from . import frozen as fz

Item = tuple[str, int, int]  # (arm, facts, slots)
CAP_FLOOR_SECONDS = 60.0  # the floor of the caps of the stages not rehearsed at real size (gates, timing, simulate, analysis, report); stated, not measured
NOT_RUN_MEMORY = "NOT RUN — BUDGET (MEMORY)"


class CapMissing(ValueError):
    """The frozen cap table has no entry for a stage or a configuration: the stage refuses."""


def rehearsal_items(plan: core.Plan | None = None) -> list[Item]:
    """Every configuration of the plan with its D-OQ cells (the rehearsal runs them all, before the cuts): 31 (30 without 2K/256)."""
    plan = plan or core.Plan()
    items: list[Item] = []
    full = dataclasses.replace(plan, dense_cut=(), lane_l=False)
    for arm in core.ARMS:
        for facts, slots in core.arm_cells(full, arm):
            items.append((arm, facts, slots))
    return items


def item_label(item: Item) -> str:
    arm, facts, slots = item
    return f"REH-{arm}-f{facts}-n{slots}"


def parse_item_label(label: str) -> Item:
    body = label.removeprefix("REH-")
    arm, rest = body.split("-f", 1)
    facts, slots = rest.split("-n")
    return arm, int(facts), int(slots)


def baseline_label(facts: int) -> str:
    return f"REH-baseline-f{facts}"


@dataclass(frozen=True)
class Rate:
    """Measured rehearsal rates of one configuration (six single-thread workers running): seconds per update (wall, 64 updates), seconds of one full evaluation (all panels and
    ablations, deep measures, robustness and the index build), the pool task's start-up overhead (task seconds minus the timed training and evaluation, paid again by every
    registered task), and the peaks (training, sampled, evaluation, pool task)."""

    seconds_per_update: float
    evaluation_seconds: float
    task_overhead_seconds: float = 0.0
    peak_rss_bytes: int = 0
    sampled_rss_bytes: int = 0
    evaluation_peak_rss_bytes: int = 0
    task_peak_rss_bytes: int = 0


Rates = dict[Item, Rate]


def rates_from_records(train: Sequence[Mapping[str, Any]], evaluation: Sequence[Mapping[str, Any]], tasks: Mapping[str, Mapping[str, float]] | None = None) -> Rates:
    """Rates from the rehearsal's whitelisted records: ``train`` the ``rehearsal.json`` records, ``evaluation`` the ``rehearsal_evaluate.json`` records (matched by ``item``),
    ``tasks`` the pool's per-task ``{label: {"seconds", "peak_rss_bytes"}}`` of the rehearse stage manifest keyed by item label. The task overhead is the task's seconds minus
    the training and evaluation seconds; never negative."""
    eval_by_item = {str(r["item"]): r for r in evaluation}
    out: Rates = {}
    for r in train:
        item = (str(r["arm"]), int(r["facts"]), int(r["slots"]))
        label = item_label(item)
        e = eval_by_item.get(label)
        e_seconds = float(e["evaluation_wall_seconds"]) if e is not None else math.nan
        task = (tasks or {}).get(label)
        overhead = max(0.0, float(task["seconds"]) - float(r["wall_seconds"]) - e_seconds) if task is not None and math.isfinite(e_seconds) else 0.0
        out[item] = Rate(
            float(r["seconds_per_update"]), e_seconds, overhead, int(r["peak_rss_bytes"]), int(r["sampled_rss_bytes"]),
            int(e["peak_rss_bytes"]) if e is not None else 0, int(task["peak_rss_bytes"]) if task is not None else 0,
        )  # fmt: skip
    return out


def missing_items(rates: Rates, plan: core.Plan | None = None) -> list[Item]:
    return [i for i in rehearsal_items(plan) if i not in rates or not math.isfinite(rates[i].evaluation_seconds)]


def cell_training_seconds(cell: core.Cell, rates: Rates, isolated: Mapping[tuple[str, int], float] | None = None, c: float = 1.0) -> float:
    """Planned updates x seconds per update plus the task start-up overhead. With ``isolated`` (the isolated wall seconds per update of the arm at the slot count) the rate is isolated x c, the
    contention ratio (section 10.3); without it, the rehearsal's six-worker rate."""
    r = rates[(cell.arm, cell.facts, cell.slots)]
    spu = r.seconds_per_update if isolated is None else isolated[(cell.arm, cell.slots)] * c
    return cell.run_updates * spu + r.task_overhead_seconds


def contention_ratio(six_workers: Mapping[tuple[str, int], float], isolated: Mapping[tuple[str, int], float]) -> dict[str, Any]:
    """c: the largest ratio of six-worker training wall seconds per update to isolated wall seconds per update of the same arm and slot count, never below 1.0 (section 10.3). A configuration
    without an isolated rate is not matched and is listed."""
    ratios = {f"{a}|{n}": v / isolated[(a, n)] for (a, n), v in six_workers.items() if (a, n) in isolated and isolated[(a, n)] > 0}
    unmatched = sorted(f"{a}|{n}" for (a, n) in six_workers if (a, n) not in isolated or isolated[(a, n)] <= 0)
    worst = max(ratios, key=lambda k: ratios[k]) if ratios else None
    c = max(core.CAP_CONTENTION_MIN, max(ratios.values(), default=core.CAP_CONTENTION_MIN))
    return {"c": c, "ratios": ratios, "worst": worst, "unmatched": unmatched}


def cell_evaluation_seconds(cell: core.Cell, rates: Rates, snapshots: int) -> float:
    """One measured full evaluation per snapshot (the rehearsed seconds per evaluated snapshot x the cell's registered snapshot count), plus the task overhead of the evaluation process."""
    r = rates[(cell.arm, cell.facts, cell.slots)]
    return snapshots * r.evaluation_seconds + r.task_overhead_seconds


def makespan(seconds: Sequence[float], workers: int = core.WORKERS) -> float:
    """Longest-processing-time list scheduling on ``workers`` single-thread workers (each job to the least loaded worker, longest first): the stage's wall time."""
    loads = [0.0] * max(1, workers)
    for s in sorted(seconds, reverse=True):
        loads[loads.index(min(loads))] += s
    return float(max(loads))


class Projection(NamedTuple):
    cells: int
    training_seconds: float
    evaluation_seconds: float
    baseline_seconds: float
    total_seconds: float


@dataclass(frozen=True)
class Fixed:
    """Wall seconds of the stages that are not scheduled over cells: the gates (rehearsed at real size on the rehearsal draw), the isolated timing and throughput stage, the
    simulation, the analysis and the report (measured on the synthetic registry). The caps of these stages are twice these figures with a stated floor."""

    gates: float = 0.0
    timing: float = 0.0
    simulate: float = 0.0
    analysis: float = 0.0
    report: float = 0.0
    generate: float = 0.0  # the registered generation and G1 of the five draws (5 x the G1 time measured on the rehearsal draw; charged before the freeze)

    @property
    def total(self) -> float:
        return self.gates + self.timing + self.simulate + self.analysis + self.report + self.generate


def stage_projection(plan: core.Plan, rates: Rates, fro: fz.Frozen, *, baseline_seconds: Mapping[int, float] | None = None, workers: int = core.WORKERS, isolated: Mapping[tuple[str, int], float] | None = None, c: float = 1.0) -> Projection:
    """Training makespan (longest first on six workers; isolated rates x c when ``isolated`` is given), evaluation makespan (every snapshot of every cell at the rehearsed seconds per evaluated
    snapshot, the baselines of every draw and fact count included) of the plan's registered cells, in analytical seconds from measured rates (task overhead included)."""
    cells = core.registered_cells(plan, dense_rates=fro.dense_rates)
    cells = [x for x in cells if x.kind != "LN"]
    train = makespan([cell_training_seconds(x, rates, isolated, c) for x in cells], workers)
    ev_jobs = [cell_evaluation_seconds(x, rates, len(fro.snapshots(x))) for x in cells]
    base = dict(baseline_seconds or {})
    facts_sets = sorted({f for f, _ in core.grid_cells(plan)})
    base_jobs = [base.get(f, 0.0) for _ in range(core.REPLICATES) for f in facts_sets]
    ev = makespan(ev_jobs + base_jobs, workers)
    return Projection(len(cells), train, ev, sum(base_jobs), train + ev)


def peak_of(rate: Rate) -> int:
    return max(rate.peak_rss_bytes, rate.sampled_rss_bytes, rate.evaluation_peak_rss_bytes, rate.task_peak_rss_bytes)


def memory_headroom(rates: Rates) -> dict[str, Any]:
    """Twice the largest peak resident size (training peak, sampled peak, evaluation peak and the pool task's peak, every configuration) within the per-worker cap (3 GiB), and six
    workers at twice that within the aggregate cap (18 GiB), i.e. a peak of at most 1.5 GiB per worker. ``status`` is NOT RUN — BUDGET (MEMORY) when the rule fails."""
    peak = max((peak_of(r) for r in rates.values()), default=0)
    per_worker = core.HEADROOM * peak <= core.RSS_WORKER_BYTES
    aggregate = core.HEADROOM * peak * core.WORKERS <= core.RSS_AGGREGATE_BYTES
    worst = max(rates, key=lambda i: peak_of(rates[i])) if rates else None
    ok = bool(per_worker and aggregate)
    return {"peak_rss_bytes": peak, "worst_item": None if worst is None else item_label(worst), "per_worker_ok": per_worker, "aggregate_ok": aggregate, "ok": ok, "status": None if ok else NOT_RUN_MEMORY, "rule": "twice the largest peak (training, sampled, evaluation, pool task) within 3 GiB per worker and 18 GiB aggregate (six workers)"}


class Headroom(NamedTuple):
    ok: bool
    charged_seconds: float
    projected_remaining_seconds: float
    required_seconds: float  # C_need = charged + 2 x remaining
    cap_seconds: float  # C_max
    shortfall_seconds: float
    cap_hours: int | None = None  # ceil(C_need / 3600) if C_need <= C_max, else None


def headroom_rule(charged_seconds: float, remaining_seconds: float, cap_max_seconds: float) -> Headroom:
    """Section 10.3: C_need = charged so far + 2 x the projected remaining time. The registered cap is C_need rounded up to the next whole hour, recorded only if it is at most C_max
    (``cap_max_seconds``, from the config: ``resources.cap_max_hours``); the hour counts are never typed."""
    need = charged_seconds + core.HEADROOM * remaining_seconds
    ok = math.isfinite(need) and need <= cap_max_seconds
    return Headroom(ok, charged_seconds, remaining_seconds, need, cap_max_seconds, max(0.0, need - cap_max_seconds), int(math.ceil(need / 3600.0)) if ok else None)


def cut_sequence(base: core.Plan | None = None) -> list[tuple[core.Plan, list[str]]]:
    """The plans of section 10.3 in the fixed order of its cuts: no cut (seed block on draws 1 and 2: draw 2 is admitted only if it fits); cut 1 (draw 2's seed block); cut 2 (draw 1's); cut 3 (D-OQ at
    8K/16K, the larger cell of control step N2). Nothing else may be cut. If none holds, NOT STARTED: BUDGET and the work returns to the human lead (no further cut is improvised)."""
    base = base or core.Plan()
    return [
        (dataclasses.replace(base, seed_block_draws=(1, 2), dense_cut=()), []),
        (dataclasses.replace(base, seed_block_draws=(1,), dense_cut=()), ["cut 1: the seed block on draw 2"]),
        (dataclasses.replace(base, seed_block_draws=(), dense_cut=()), ["cut 1: the seed block on draw 2", "cut 2: the seed block on draw 1"]),
        (dataclasses.replace(base, seed_block_draws=(), dense_cut=core.DOQ_CUTTABLE), ["cut 1: the seed block on draw 2", "cut 2: the seed block on draw 1", "cut 3: D-OQ at 8K/16K"]),
    ]


NOT_STARTED_BUDGET = "NOT STARTED: BUDGET"


@dataclass
class CutResult:
    ok: bool
    plan: core.Plan | None
    applied_cuts: list[str]
    headroom: Headroom | None
    projection: Projection | None
    memory: dict[str, Any]
    tried: list[dict[str, Any]] = field(default_factory=list)
    returns_to_lead: str | None = None


def choose_plan(
    rates: Rates,
    fixed: Fixed,
    cpu_per_update: dict[tuple[str, int], float],
    *,
    charged_seconds: float,
    cap_max_seconds: float,
    base: core.Plan | None = None,
    baseline_seconds: Mapping[int, float] | None = None,
    frozen_kwargs: Mapping[str, Any] | None = None,
    isolated: Mapping[tuple[str, int], float] | None = None,
    c: float = 1.0,
) -> CutResult:
    """Apply the cuts of section 10.3 in order until C_need is at most C_max. Memory is judged first: a failed memory rule is NOT RUN — BUDGET (MEMORY) and no cut helps (the evaluation batch is
    reduced and the rehearsal repeated). If no plan holds after the last cut, NOT STARTED: BUDGET: the work returns to the human lead with the measured figure; no further cut is improvised."""
    memory = memory_headroom(rates)
    tried: list[dict[str, Any]] = []
    if not memory["ok"]:
        return CutResult(False, None, [], None, None, memory, tried, "memory: twice the measured peak exceeds the memory caps; reduce the evaluation batch and repeat the rehearsal")
    last: tuple[Headroom, Projection] | None = None
    for plan, cuts in cut_sequence(base):
        fro = fz.Frozen.build(plan, cpu_per_update, **dict(frozen_kwargs or {}))
        proj = stage_projection(plan, rates, fro, baseline_seconds=baseline_seconds, isolated=isolated, c=c)
        remaining = proj.total_seconds + fixed.total
        hr = headroom_rule(charged_seconds, remaining, cap_max_seconds)
        tried.append({"plan": plan.as_json(), "cuts": cuts, "remaining_seconds": remaining, "required_seconds": hr.required_seconds, "ok": hr.ok})
        last = (hr, proj)
        if hr.ok:
            return CutResult(True, plan, cuts, hr, proj, memory, tried)
    assert last is not None
    return CutResult(False, None, tried[-1]["cuts"], last[0], last[1], memory, tried, f"{NOT_STARTED_BUDGET}: C_need {last[0].required_seconds / 3600:.2f} h exceeds C_max {cap_max_seconds / 3600:.2f} h after the last cut (shortfall {last[0].shortfall_seconds:.0f} s); the work returns to the human lead with the measured figure")


# --- caps -------------------------------------------------------------------------------------------------------------------------------------------------
def caps_table(rates: Rates, fixed: Fixed, cpu_per_update: dict[tuple[str, int], float], *, base: core.Plan | None = None, baseline_seconds: Mapping[int, float] | None = None, frozen_kwargs: Mapping[str, Any] | None = None, floor_seconds: float = CAP_FLOOR_SECONDS, isolated: Mapping[tuple[str, int], float] | None = None, c: float = 1.0) -> dict[str, Any]:
    """The frozen cap table (``studies/p10s1/freeze/stage_caps.json``): one source of truth. Each cap is twice the projection (task start-up included) of what it bounds. Training and evaluation
    have an entry per possible configuration (the plan's key: seed-block draws, the D-OQ cut, 2K/256 present or absent); gates, timing, simulate, analysis and report are twice a measured time with a
    stated floor. A stage whose configuration has no entry refuses."""
    configs: dict[str, Any] = {}
    for plan in core.plan_configurations(base):
        fro = fz.Frozen.build(plan, cpu_per_update, **dict(frozen_kwargs or {}))
        p = stage_projection(plan, rates, fro, baseline_seconds=baseline_seconds, isolated=isolated, c=c)
        configs[plan.key()] = {"cells": p.cells, "train": core.HEADROOM * p.training_seconds, "evaluate": core.HEADROOM * p.evaluation_seconds, "projection": p._asdict()}
    return {
        "rule": "each cap = 2 x the projection (task start-up included); gates, timing, simulate, analysis and report: 2 x a measured time with the stated floor", "floor_seconds": floor_seconds,
        "gates": max(floor_seconds, core.HEADROOM * fixed.gates), "timing": max(floor_seconds, core.HEADROOM * fixed.timing), "simulate": max(floor_seconds, core.HEADROOM * fixed.simulate),
        "analysis": max(floor_seconds, core.HEADROOM * fixed.analysis), "report": max(floor_seconds, core.HEADROOM * fixed.report), "configurations": configs,
    }  # fmt: skip


def cap_for(table: Mapping[str, Any], stage: str, plan: core.Plan) -> float:
    """The cap in seconds of ``stage`` (``gates``, ``train``, ``evaluate``, ``timing``, ``simulate``, ``analysis``, ``report``) for the plan's configuration; a stage or configuration
    with no entry raises ``CapMissing`` (the stage refuses)."""
    if stage in ("train", "evaluate"):
        entry = table.get("configurations", {}).get(plan.key())
        if entry is None or stage not in entry:
            raise CapMissing(f"the frozen cap table has no entry for {stage} at configuration {plan.key()}")
        return float(entry[stage])
    if stage not in table or not isinstance(table[stage], int | float):
        raise CapMissing(f"the frozen cap table has no entry for {stage!r}")
    return float(table[stage])


def exceeds_remaining(cap_seconds: float, remaining_seconds: float) -> bool:
    """A stage refuses to start if the remaining cap is below its stage cap (the ledger's rule, as a pure function)."""
    return remaining_seconds < cap_seconds


# --- the calibration's items: projections and caps (section 10.1 item 0a; audit B1) ----------------------------------------------------------
ITEM_GROUPS = (("row-up", "load"), ("h8", "dense"), ("load-ext",))  # the last group is the one-time extension of the load search (section 25.15), its own pooled stage; # the items of one pooled stage, in the order the pool is given their tasks: the short row-U_P runs first, so that no run waits for the long load-search runs


def dispatch_order(items: Sequence[str], unit: int = core.U_P, row_u_p: Mapping[int, int] | None = None) -> list[tuple[str, core.Cell]]:
    """The calibration cells of ``items`` in the exact order their tasks are handed to the pool (which starts pending tasks in list order, each on the first free worker): the items in the order of
    ``ITEM_GROUPS``, within an item the longest run first (then the label)."""
    rows = row_u_p or {f: max(core.row_u_p_candidates(unit)) for f in core.ROW_FACTS}
    order = [i for g in ITEM_GROUPS for i in g if i in items]
    out: list[tuple[str, core.Cell]] = []
    for item in order:
        cells = core.calibration_cells_of([item], rows, unit)
        out += [(item, c) for c in sorted(cells, key=lambda c: (-c.run_updates, c.label))]
    return out


def simulate_dispatch(durations: Sequence[float], workers: int = core.WORKERS) -> list[tuple[float, float]]:
    """(start, end) seconds from the stage start of each task, the tasks taken in list order and each started on the first free worker (the pool's dispatch)."""
    free = [0.0] * max(1, workers)
    out: list[tuple[float, float]] = []
    for d in durations:
        k = free.index(min(free))
        out.append((free[k], free[k] + d))
        free[k] += d
    return out


def item_runs(unit: int = core.U_P, row_u_p: Mapping[int, int] | None = None) -> dict[str, list[tuple[str, int, int]]]:
    """The training jobs of each calibration item as (arm, slots, updates). Before item 1 has fixed the rows, items h8 and dense are projected at the largest candidate U_P of every row (the conservative
    reading: a longer run, a larger cap)."""
    out: dict[str, list[tuple[str, int, int]]] = {}
    for item, c in dispatch_order([i for g in ITEM_GROUPS for i in g], unit, row_u_p):
        out.setdefault(item, []).append((c.arm, c.slots, c.run_updates))
    return out


def item_projection(
    wall_per_update: Mapping[tuple[str, int], float],
    unit: int = core.U_P,
    row_u_p: Mapping[int, int] | None = None,
    workers: int = core.WORKERS,
    startup_seconds: float = 0.0,
    evaluation_seconds: Mapping[tuple[str, int, int], float] | None = None,
) -> dict[str, Any]:
    """Item 0a (ADR-0021 section 25.14 item 1): for every calibration item, the projected completion time of its last run from the stage start **under the exact pooled dispatch order**
    (``dispatch_order`` and ``simulate_dispatch``, one pooled stage per ``ITEM_GROUPS`` entry), where a run takes its start-up (``startup_seconds``, measured by the preview), its training (isolated
    wall seconds per update, from the preview) and its evaluation (the preview's seconds per evaluated snapshot of the run's arm, facts and slots, times its number of snapshots); and the item's
    cap, twice that (``core.HEADROOM``), a deadline counted from the stage start. A configuration the preview did not time is listed and the item has no projection (it is not started on an assumed
    cost). Without ``evaluation_seconds`` the evaluation is not included (unit tests only; the calibration command requires them)."""
    from .calibrate import calibration_snapshots

    out: dict[str, Any] = {}
    for group in ITEM_GROUPS:
        ordered = dispatch_order(group, unit, row_u_p)
        missing = {item: sorted({f"{c.arm}|{c.slots}" for i, c in ordered if i == item and (c.arm, c.slots) not in wall_per_update} | ({f"{c.arm}|{c.facts}|{c.slots}" for i, c in ordered if i == item and evaluation_seconds is not None and (c.arm, c.facts, c.slots) not in evaluation_seconds})) for item in group}
        if any(missing.values()):
            for item in group:
                out[item] = {"runs": sum(1 for i, _c in ordered if i == item), "projected_wall_seconds": None, "cap_seconds": None, "missing_rates": sorted(set().union(*missing.values()))}
            continue

        def duration(c: core.Cell) -> float:
            ev = 0.0 if evaluation_seconds is None else evaluation_seconds[(c.arm, c.facts, c.slots)] * len(calibration_snapshots(c))
            return startup_seconds + c.run_updates * wall_per_update[(c.arm, c.slots)] + ev

        times = simulate_dispatch([duration(c) for _i, c in ordered], workers)
        for item in group:
            ends = [end for (i, _c), (_s, end) in zip(ordered, times, strict=True) if i == item]
            out[item] = {"runs": len(ends), "projected_wall_seconds": max(ends), "cap_seconds": core.HEADROOM * max(ends), "missing_rates": [], "startup_seconds": startup_seconds, "evaluation_included": evaluation_seconds is not None}
    return out
