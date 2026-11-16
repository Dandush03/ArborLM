# ruff: noqa: E501
"""P10S1 budgets, caps, frozen tables and calibration rules (ADR-0021 sections 5.4, 10): rates with task start-up time, the projection, the headroom rule with evaluation peaks in the
memory rule, the cuts in their fixed order, the cap table (one entry per configuration), the matched-compute plan, and the calibration's fixed rule table. Pure functions on
constructed numbers; nothing is trained and no seed is read. Self-check only: not independent review, not Astra validation, not human approval."""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from studies.p10s1 import budget, core  # noqa: E402
from studies.p10s1 import frozen as fz  # noqa: E402

GIB = 1024**3


def make_rates(spu: float = 0.01, evaluation: float = 5.0, overhead: float = 2.0, peak: int = int(0.7 * GIB), plan: core.Plan | None = None) -> budget.Rates:
    return {i: budget.Rate(spu * (1 + core.work_formula("F-OQ" if i[0] == "D-OQ" else i[0], i[2])["W"] / 1e5), evaluation, overhead, peak, peak, peak, peak) for i in budget.rehearsal_items(plan or core.Plan())}


CPU = fz.default_cpu_table()


# --- rates and projections ------------------------------------------------------------------------------------------------------------------
def test_rates_include_task_startup_time() -> None:
    train = [{"arm": "F-OQ", "facts": 2048, "slots": 4096, "wall_seconds": 4.0, "seconds_per_update": 0.0625, "peak_rss_bytes": 100, "sampled_rss_bytes": 90, "label": "x"}]
    ev = [{"item": budget.item_label(("F-OQ", 2048, 4096)), "evaluation_wall_seconds": 2.0, "peak_rss_bytes": 300}]
    tasks = {budget.item_label(("F-OQ", 2048, 4096)): {"seconds": 9.5, "peak_rss_bytes": 400}}
    r = budget.rates_from_records(train, ev, tasks)[("F-OQ", 2048, 4096)]
    assert r.task_overhead_seconds == pytest.approx(3.5) and r.evaluation_seconds == 2.0 and r.evaluation_peak_rss_bytes == 300 and r.task_peak_rss_bytes == 400
    assert budget.rates_from_records(train, ev, {budget.item_label(("F-OQ", 2048, 4096)): {"seconds": 1.0, "peak_rss_bytes": 1}})[("F-OQ", 2048, 4096)].task_overhead_seconds == 0.0  # never negative
    assert budget.missing_items(budget.rates_from_records(train, [], tasks))[0] in budget.rehearsal_items() and len(budget.missing_items(budget.rates_from_records(train, ev, tasks))) == 30


def test_projection_adds_overhead_to_every_task() -> None:
    plan = core.Plan(seed_block_draws=())
    fro = fz.Frozen.build(plan, CPU)
    base, with_overhead = make_rates(overhead=0.0), make_rates(overhead=10.0)
    cell = core.registered_cells(plan)[0]
    assert budget.cell_training_seconds(cell, with_overhead) - budget.cell_training_seconds(cell, base) == pytest.approx(10.0)
    snaps = len(fro.snapshots(cell))
    assert budget.cell_evaluation_seconds(cell, with_overhead, snaps) - budget.cell_evaluation_seconds(cell, base, snaps) == pytest.approx(10.0)
    p0, p1 = budget.stage_projection(plan, base, fro), budget.stage_projection(plan, with_overhead, fro)
    assert p1.training_seconds > p0.training_seconds and p1.evaluation_seconds > p0.evaluation_seconds and p1.cells == 155 and p0.total_seconds == pytest.approx(p0.training_seconds + p0.evaluation_seconds)
    with_base = budget.stage_projection(plan, base, fro, baseline_seconds={2048: 30.0, 8192: 30.0, 32768: 30.0})
    assert with_base.baseline_seconds == 30.0 * 15 and with_base.evaluation_seconds >= p0.evaluation_seconds


def test_makespan_is_list_scheduling() -> None:
    assert budget.makespan([], 6) == 0.0 and budget.makespan([5.0], 6) == 5.0
    assert budget.makespan([6.0] * 6, 6) == 6.0 and budget.makespan([6.0] * 7, 6) == 12.0
    assert budget.makespan([10.0, 9.0, 8.0, 1.0, 1.0, 1.0], 2) == 17.0
    assert budget.makespan([4.0, 3.0, 3.0, 2.0], 2) == 6.0


# --- memory rule (evaluation peaks included) ---------------------------------------------------------------------------------------------------
def test_memory_rule_includes_evaluation_and_pool_peaks() -> None:
    train_only = int(0.7 * GIB)
    ok = make_rates(peak=train_only)
    assert budget.memory_headroom(ok)["ok"]
    items = list(ok)
    # the training peaks are fine; one 65,536-slot evaluation peaks at 1.529 GiB: 2 x 1.529 = 3.06 GiB > 3 GiB (the P9-II audit M2 case)
    high_eval = dict(ok)
    high_eval[items[0]] = budget.Rate(0.01, 5.0, 2.0, train_only, train_only, int(1.529 * GIB), train_only)
    m = budget.memory_headroom(high_eval)
    assert not m["ok"] and not m["per_worker_ok"] and m["status"] == budget.NOT_RUN_MEMORY and m["worst_item"] == budget.item_label(items[0])
    high_task = dict(ok)
    high_task[items[1]] = budget.Rate(0.01, 5.0, 2.0, train_only, train_only, train_only, int(1.6 * GIB))
    assert not budget.memory_headroom(high_task)["ok"]
    at_limit = {i: budget.Rate(0.01, 5.0, 2.0, int(1.5 * GIB), 0, 0, 0) for i in items}
    assert budget.memory_headroom(at_limit)["ok"]  # 2 x 1.5 GiB = 3 GiB per worker and 6 x 3 GiB = 18 GiB aggregate
    assert not budget.memory_headroom({i: budget.Rate(0.01, 5.0, 2.0, int(1.5 * GIB) + 1, 0, 0, 0) for i in items})["ok"]
    assert core.PEAK_PER_WORKER_FOR_HEADROOM == 1.5 * GIB and core.RSS_AGGREGATE_BYTES == 18 * GIB


# --- the headroom rule and the cuts -----------------------------------------------------------------------------------------------------------
def test_headroom_rule() -> None:
    cap = core.cap_seconds()  # the cap is the config value, never a literal
    zero = budget.headroom_rule(1.4 * 3600, 5.3 * 3600, cap)  # the ADR's projection arithmetic: 1.4 h + 2 x 5.3 h = 12.0 h
    assert zero.required_seconds == pytest.approx(12.0 * 3600) and zero.ok is (12.0 * 3600 <= cap)
    assert budget.headroom_rule(5040.0, 18000.0, cap).ok and budget.headroom_rule(5040.0, 18000.0, cap).required_seconds == 41040.0
    exact = (cap - 5040.0) / 2.0
    assert budget.headroom_rule(5040.0, exact, cap).ok and budget.headroom_rule(5040.0, exact, cap).required_seconds == pytest.approx(cap)  # exactly at the cap
    over = budget.headroom_rule(5040.0, exact + 20.0, cap)
    assert not over.ok and over.shortfall_seconds == pytest.approx(40.0) and over.charged_seconds == 5040.0
    assert not budget.headroom_rule(0.0, math.inf, 1e9).ok
    assert budget.headroom_rule(5040.0, exact + 20.0, cap + 3600.0).ok  # the cap is an argument: a larger cap admits it
    assert budget.exceeds_remaining(100.0, 99.0) and not budget.exceeds_remaining(100.0, 100.0)


# --- frozen tables: costs, the MC plan, snapshots ---------------------------------------------------------------------------------------------
# --- calibration rules --------------------------------------------------------------------------------------------------------------------------
def test_lane_l_status_labels_and_it_is_never_enabled_by_default() -> None:
    assert fz.lane_l_status(None) == fz.LANE_OMITTED_NO_INTERFACE == "OMITTED — no interface qualified before the freeze"
    for outcome in ("ADDRESSING-NOT-QUALIFIED", "INCONCLUSIVE", "ENGINEERING_FAIL", "INCOMPLETE", "NOT STARTED"):
        assert fz.lane_l_status(outcome, "A5-C", True) == fz.LANE_OMITTED_NO_INTERFACE
    assert fz.lane_l_status(fz.LANE_QUALIFIED_4096, "A5-C", True) == "OMITTED — QUALIFIED AT 4,096 ONLY"
    assert fz.lane_l_status(fz.LANE_QUALIFIED_BOTH, "A1", True) == "OMITTED — SUPERVISED ARM HAS NO 8K/4K CELL" == fz.lane_l_status(fz.LANE_QUALIFIED_BOTH, "A2", False)
    assert fz.lane_l_status(fz.LANE_QUALIFIED_BOTH, "A5-C", False) == "OMITTED — NOT OVERLOAD-QUALIFIED"
    assert fz.lane_l_status(fz.LANE_QUALIFIED_BOTH, "A5-C", True) == fz.LANE_WOULD_RUN
    assert core.Plan().lane_l is False and fz.Frozen().lane_status == fz.LANE_OMITTED_NO_INTERFACE and fz.Frozen().s0_status == "S0 NOT YET DECIDED"
