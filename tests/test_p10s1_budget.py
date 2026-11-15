# ruff: noqa: E501
"""P10S1 budgets, caps, frozen tables and calibration rules (ADR-0021 sections 5.4, 10): rates with task start-up time, the projection, the headroom rule with evaluation peaks in the
memory rule, the cuts in their fixed order, the cap table (one entry per configuration), the matched-compute plan, and the calibration's fixed rule table. Pure functions on
constructed numbers; nothing is trained and no seed is read. Self-check only: not independent review, not Astra validation, not human approval."""

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from studies.p10s1 import budget, calibrate, core  # noqa: E402
from studies.p10s1 import classes as C  # noqa: E402
from studies.p10s1 import frozen as fz  # noqa: E402

GIB = 1024**3


def make_rates(spu: float = 0.01, evaluation: float = 5.0, overhead: float = 2.0, peak: int = int(0.7 * GIB), plan: core.Plan | None = None) -> budget.Rates:
    return {i: budget.Rate(spu * (1 + core.work_formula("F-OQ" if i[0] == "D-OQ" else i[0], i[2])["W"] / 1e5), evaluation, overhead, peak, peak, peak, peak) for i in budget.rehearsal_items(plan or core.Plan())}


CPU = fz.default_cpu_table()


# --- rates and projections ------------------------------------------------------------------------------------------------------------------
def test_rehearsal_items_cover_the_30_configurations() -> None:
    items = budget.rehearsal_items()
    assert len(items) == 30 and len(set(items)) == 30
    assert len(budget.rehearsal_items(core.Plan(overload_u_p=8192))) == 38
    assert len(budget.rehearsal_items(core.Plan(dense_cut=("8K/64K",)))) == 30  # the rehearsal runs every configuration before any cut
    for i in items:
        assert budget.parse_item_label(budget.item_label(i)) == i


def test_rates_include_task_startup_time() -> None:
    train = [{"arm": "F-OQ", "facts": 2048, "slots": 4096, "wall_seconds": 4.0, "seconds_per_update": 0.0625, "peak_rss_bytes": 100, "sampled_rss_bytes": 90, "label": "x"}]
    ev = [{"item": budget.item_label(("F-OQ", 2048, 4096)), "evaluation_wall_seconds": 2.0, "peak_rss_bytes": 300}]
    tasks = {budget.item_label(("F-OQ", 2048, 4096)): {"seconds": 9.5, "peak_rss_bytes": 400}}
    r = budget.rates_from_records(train, ev, tasks)[("F-OQ", 2048, 4096)]
    assert r.task_overhead_seconds == pytest.approx(3.5) and r.evaluation_seconds == 2.0 and r.evaluation_peak_rss_bytes == 300 and r.task_peak_rss_bytes == 400
    assert budget.rates_from_records(train, ev, {budget.item_label(("F-OQ", 2048, 4096)): {"seconds": 1.0, "peak_rss_bytes": 1}})[("F-OQ", 2048, 4096)].task_overhead_seconds == 0.0  # never negative
    assert budget.missing_items(budget.rates_from_records(train, [], tasks))[0] in budget.rehearsal_items() and len(budget.missing_items(budget.rates_from_records(train, ev, tasks))) == 29


def test_projection_adds_overhead_to_every_task() -> None:
    plan = core.Plan(seed_block_draws=())
    fro = fz.Frozen.build(plan, CPU)
    base, with_overhead = make_rates(overhead=0.0), make_rates(overhead=10.0)
    cell = core.registered_cells(plan)[0]
    assert budget.cell_training_seconds(cell, with_overhead) - budget.cell_training_seconds(cell, base) == pytest.approx(10.0)
    snaps = len(fro.snapshots(cell))
    assert budget.cell_evaluation_seconds(cell, with_overhead, snaps) - budget.cell_evaluation_seconds(cell, base, snaps) == pytest.approx(10.0)
    p0, p1 = budget.stage_projection(plan, base, fro), budget.stage_projection(plan, with_overhead, fro)
    assert p1.training_seconds > p0.training_seconds and p1.evaluation_seconds > p0.evaluation_seconds and p1.cells == 150 and p0.total_seconds == pytest.approx(p0.training_seconds + p0.evaluation_seconds)
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


def test_cuts_in_their_fixed_order() -> None:
    both = budget.cut_sequence({"8K/64K": True, "32K/16K": True})
    assert [p.seed_block_draws for p, _ in both] == [(1, 2), (1,), (), (), ()] and [p.dense_cut for p, _ in both] == [(), (), (), ("8K/64K",), ("8K/64K", "32K/16K")]
    assert both[1][1] == ["cut 1: the seed block on draw 2"] and both[3][1][-1] == "cut 3: D-OQ at 8K/64K"
    only32 = budget.cut_sequence({"8K/64K": False, "32K/16K": True})
    assert [p.dense_cut for p, _ in only32] == [(), (), (), ("32K/16K",)]  # a cell that was predicted loaded (8K/64K here) is never cut
    none = budget.cut_sequence({"8K/64K": False, "32K/16K": False})
    assert len(none) == 3 and all(p.dense_cut == () for p, _ in none)  # cut 3 has no eligible cell: nothing else may be cut
    assert all(p.unit == 16 for p, _ in budget.cut_sequence({}, None, 16))


def choose(spu: float, *, charged: float, cap: float, eligible: dict[str, bool] | None = None, peak: int = int(0.7 * GIB), evaluation: float = 5.0) -> budget.CutResult:
    rates = make_rates(spu=spu, peak=peak, evaluation=evaluation)
    return budget.choose_plan(rates, budget.Fixed(60.0, 300.0, 60.0, 30.0, 30.0), CPU, charged_seconds=charged, cap_seconds=cap, eligible_doq=eligible or {})


def test_choose_plan_applies_the_cuts_until_the_rule_holds() -> None:
    cap = core.cap_seconds()
    easy = choose(0.0005, charged=3000.0, cap=cap)
    assert easy.ok and easy.applied_cuts == [] and easy.plan == core.Plan(None, (1, 2), ())
    # scan the per-update rate: somewhere the full plan stops fitting and the plan without draw 2's seed block still does; the cuts are tried in order, never skipped
    found = None
    spu = 0.0005
    while spu < 0.2 and found is None:
        r = choose(spu, charged=3000.0, cap=cap, eligible={"8K/64K": True, "32K/16K": True})
        if r.ok and r.applied_cuts == ["cut 1: the seed block on draw 2"]:
            found = r
        spu *= 1.01
    assert found is not None and found.plan == core.Plan(None, (1,), ()) and [t["ok"] for t in found.tried] == [False, True]
    deeper = None
    spu = 0.0005
    while spu < 0.2 and deeper is None:
        r = choose(spu, charged=3000.0, cap=cap, eligible={"8K/64K": True, "32K/16K": True})
        if r.ok and r.applied_cuts and r.applied_cuts[-1] == "cut 3: D-OQ at 8K/64K":
            deeper = r
        spu *= 1.01
    assert deeper is not None and deeper.plan is not None and deeper.plan.dense_cut == ("8K/64K",) and deeper.plan.seed_block_draws == ()
    for r in (found, deeper):
        tried = [t["cuts"] for t in r.tried]
        assert tried == sorted(tried, key=len)
    # nothing fits: cut 4, the work returns to the human lead with the measured shortfall and the options
    hopeless = choose(1.0, charged=3000.0, cap=cap, eligible={"8K/64K": True, "32K/16K": True})
    assert not hopeless.ok and hopeless.plan is None and hopeless.headroom is not None and hopeless.headroom.shortfall_seconds > 0
    assert "raise the cap" in (hopeless.returns_to_lead or "") and "shorten the run lengths" in (hopeless.returns_to_lead or "") and len(hopeless.tried) == 5
    no_eligible = choose(1.0, charged=3000.0, cap=cap)
    assert not no_eligible.ok and len(no_eligible.tried) == 3  # D-OQ is not cut where the calibration predicted the smaller cell loaded
    bad_memory = choose(0.0005, charged=3000.0, cap=cap, peak=int(1.6 * GIB))
    assert not bad_memory.ok and "memory" in (bad_memory.returns_to_lead or "") and bad_memory.tried == []
    # the cap is an argument: a larger cap admits the full plan
    r_small = choose(0.02, charged=3000.0, cap=6 * 3600.0)
    r_large = choose(0.02, charged=3000.0, cap=16 * 3600.0)
    assert len(r_large.tried) <= len(r_small.tried) and (r_large.ok or not r_small.ok)


def test_caps_table_has_one_entry_per_configuration() -> None:
    rates = make_rates()
    fixed = budget.Fixed(100.0, 400.0, 50.0, 20.0, 10.0)
    table = budget.caps_table(rates, fixed, CPU)
    assert len(table["configurations"]) == 12
    for plan in core.plan_configurations():
        entry = table["configurations"][plan.key()]
        fro = fz.Frozen.build(plan, CPU)
        proj = budget.stage_projection(plan, rates, fro)
        assert entry["train"] == pytest.approx(2.0 * proj.training_seconds) and entry["evaluate"] == pytest.approx(2.0 * proj.evaluation_seconds)
        assert budget.cap_for(table, "train", plan) == entry["train"] and budget.cap_for(table, "evaluate", plan) == entry["evaluate"]
    assert table["gates"] == 200.0 and table["timing"] == 800.0 and table["simulate"] == 100.0 and table["analysis"] == budget.CAP_FLOOR_SECONDS and table["report"] == budget.CAP_FLOOR_SECONDS
    cuts = [budget.cap_for(table, "train", p) for p in core.plan_configurations()]
    assert min(cuts) < max(cuts)  # a cut configuration has a smaller cap
    with pytest.raises(budget.CapMissing):
        budget.cap_for(table, "train", core.Plan(overload_u_p=8192))  # the overload row has no entry unless the freeze built one
    with pytest.raises(budget.CapMissing):
        budget.cap_for(table, "stage9", core.Plan())
    with pytest.raises(budget.CapMissing):
        budget.cap_for({"configurations": {}}, "evaluate", core.Plan())
    overloaded = budget.caps_table(make_rates(plan=core.Plan(overload_u_p=8192)), fixed, CPU, overload_u_p=8192)
    assert budget.cap_for(overloaded, "train", core.Plan(overload_u_p=8192, seed_block_draws=(1,))) > 0
    json.dumps(table)


# --- frozen tables: costs, the MC plan, snapshots ---------------------------------------------------------------------------------------------
def test_cost_tables_and_matched_compute_plan() -> None:
    assert fz.trainable_parameters("F-OQ", 4096) == core.foq_trainable_parameters(4096) and fz.trainable_parameters("D-OQ", 4096) == core.doq_trainable_parameters(core.doq_hidden(4096))
    assert fz.analytic_madds_per_update("F-OQ", 4096) == 3 * 128 * 66816 + 4 * 197633
    fro = fz.Frozen.build(core.Plan(seed_block_draws=()), CPU)
    keys = set(fro.mc)
    for arm in ("F-OQ", "T-OQ", "H8"):
        assert {f"cap|{arm}|{s}" for s in ("A1", "A2", "B1", "B2")} <= keys
    assert {f"diag|{arm}|{k}" for arm in ("F-OQ", "T-OQ") for k in (0, 1)} <= keys and "dense|F-OQ|8K/16K" in keys and "dense|H8|32K/64K" in keys
    assert {k for k in keys if k.startswith("dense|F-OQ")} == {f"dense|F-OQ|{n}" for n in ("8K/16K", "8K/64K", "32K/16K", "32K/64K")}
    e = fro.mc["cap|F-OQ|A1"]
    assert e.ok() and e.cheaper == "small" and e.large_update == core.U_P and e.small_update in {int(g * core.U_P) for g in core.MC_GRID} and e.multiplier >= 1.0
    cut = fz.Frozen.build(core.Plan(seed_block_draws=(), dense_cut=("8K/64K",)), CPU)
    assert "dense|F-OQ|8K/64K" not in cut.mc and "dense|F-OQ|32K/16K" in cut.mc  # no D-OQ cell there: no pair
    need = fz.required_snapshots(fro.plan, fro.mc)
    small = next(c for c in core.registered_cells(fro.plan) if (c.arm, c.facts, c.slots) == ("F-OQ", 8192, 4096))
    assert e.small_update in fro.snapshots(small) and set(fro.snapshots(small)) >= set(core.snapshot_updates(core.U_P, small.run_updates)) and ("F-OQ", 8192, 4096) in need
    for c in core.registered_cells(fro.plan):
        s = fro.snapshots(c)
        assert s[-1] == c.run_updates and c.run_updates // 2 in s and core.U_P in s and all(1 <= u <= c.run_updates for u in s)
    assert fro.entry("cap|nope|A1").status == C.MC_SHORT  # a pair the freeze did not record is not established


def test_frozen_round_trip() -> None:
    fro = fz.Frozen.build(core.Plan(seed_block_draws=(1,), dense_cut=("8K/64K",)), CPU, dense_rates={4096: 0.003, 16384: 0.01, 65536: 0.001}, h8_undertrained=["8K/16K"], s0_status="S0 TEST", no_loaded_transitions=["16K→64K"], cuts=["cut 3"])
    back = fz.Frozen.from_json(json.loads(json.dumps(fro.as_json())))
    assert back.as_json() == fro.as_json() and back.plan == fro.plan and back.mc == fro.mc and back.dense_rates == {4096: 0.003, 16384: 0.01, 65536: 0.001}
    rated = core.registered_cells(fro.plan, dense_rates=fro.dense_rates)
    assert {c.lr for c in rated if c.arm == "D-OQ" and c.slots == 16384} == {0.01} and {c.lr for c in rated if c.arm == "D-OQ" and c.slots == 65536} == {0.001} and {c.lr for c in rated if c.arm != "D-OQ"} == {0.003}


# --- calibration rules --------------------------------------------------------------------------------------------------------------------------
def loads(**flags: bool) -> dict[tuple[int, int], bool]:
    base = {(4096, f): False for f in (8192, 16384, 32768, 65536)} | {(16384, f): False for f in (8192, 32768, 65536, 131072)}
    names = {"s8": (4096, 8192), "s32": (4096, 32768), "l8k": (16384, 8192), "l32": (16384, 32768), "l64": (16384, 65536), "l128": (16384, 131072)}
    for k, v in flags.items():
        base[names[k]] = v
    return base


def test_load_rule_table() -> None:
    d = calibrate.load_decision(loads(s8=True, l32=True))
    assert d.action == calibrate.GRID_STANDS and d.overload_facts is None
    assert calibrate.load_decision(loads(s32=True, l32=True)).action == calibrate.GRID_STANDS  # load 2 or load 8 at 4,096 slots
    assert calibrate.load_decision(loads(s8=True, s32=True, l32=True, l64=True)).action == calibrate.GRID_STANDS  # load 2 loaded at 16K: the grid stands
    r = calibrate.load_decision(loads(s8=True, l64=True))
    assert r.action == calibrate.OVERLOAD_ROW and r.overload_facts == 65536 and "prediction only" in r.note
    assert calibrate.load_decision(loads(l32=True)).action == calibrate.RETURN_TO_LEAD  # no registered 4,096-slot cell predicted loaded
    assert calibrate.load_decision(loads(s8=True, l128=True)).action == calibrate.RETURN_TO_LEAD  # only load 8 at 16K: 131,072 facts exceed 65,536 slots
    assert calibrate.load_decision(loads(s8=True)).action == calibrate.RETURN_TO_LEAD  # none at 16K
    assert calibrate.load_decision(loads(s8=True, l64=True, l128=True)).action == calibrate.OVERLOAD_ROW
    assert calibrate.cut3_eligibility(loads(s32=True, l8k=True)) == {"8K/64K": False, "32K/16K": False}
    assert calibrate.cut3_eligibility(loads(s8=True)) == {"8K/64K": True, "32K/16K": True}  # the load-0.5 cell and 32K/4K predicted not loaded
    assert calibrate.cut3_eligibility(loads(s32=True)) == {"8K/64K": True, "32K/16K": False}


def test_dense_rate_tie_is_not_resolved_by_code() -> None:
    assert calibrate.select_dense_rate({0.001: 0.30, 0.003: 0.50, 0.01: 0.20})["rate"] == 0.003
    with pytest.raises(calibrate.TieNeedsLead):
        calibrate.select_dense_rate({0.001: 0.30, 0.003: 0.31, 0.01: 0.10})  # a difference below 0.02: the ADR's 'faster of the two' is undefined
    with pytest.raises(calibrate.TieNeedsLead):
        calibrate.select_dense_rate({0.001: 0.5, 0.003: 0.5, 0.01: 0.5})
    assert calibrate.select_dense_rate({0.001: 0.30, 0.003: 0.50, 0.01: 0.4799})["rate"] == 0.003  # 0.0201 below the best: not a tie
    with pytest.raises(calibrate.TieNeedsLead):
        calibrate.select_dense_rate({0.001: 0.30, 0.003: 0.50, 0.01: 0.4801})  # 0.0199 below the best: still a tie
    assert "dense_rate_tie" in C.READINGS
    with pytest.raises(calibrate.TieNeedsLead):
        calibrate.dense_rates_of({"dense_rates": {"16384": {"rate": None}, "65536": {"rate": 0.003}}})
    assert calibrate.dense_rates_of({"dense_rates": {"16384": {"rate": 0.01}, "65536": {"rate": 0.001}}}) == {16384: 0.01, 65536: 0.001, 4096: 0.01}


def test_u_p_check_h8_and_overload_u_p() -> None:
    full = {(arm, cell, d, p): 0.99 for arm in ("R2", "F-OQ") for cell in ("2K/4K", "8K/16K", "32K/64K") for d in (1, 2) for p in ("A", "B")}
    assert calibrate.u_p_check(full)["stands"] and calibrate.u_p_check(full)["action"] == "none"
    low = dict(full)
    low[("F-OQ", "32K/64K", 2, "B")] = 0.89
    r = calibrate.u_p_check(low)
    assert not r["stands"] and r["action"] == calibrate.RETURN_TO_LEAD and r["failures"][0]["needed"] == 0.90  # no larger U_P is substituted by rule
    low2 = dict(full)
    low2[("R2", "2K/4K", 1, "A")] = 0.94
    assert not calibrate.u_p_check(low2)["stands"]
    assert not calibrate.u_p_check({k: v for k, v in full.items() if k[2] == 1})["stands"]  # a missing accuracy is a failure
    h8 = calibrate.h8_report({("2K/4K", 1, "A"): 0.95, ("8K/16K", 1, "A"): 0.85, ("8K/16K", 2, "B"): 0.92})
    assert h8["undertrained_cells"] == ["8K/16K"]
    acc_f = {(u, d, p): (0.5 if u == 8192 else 0.92 if u == 16384 else 0.95) for u in (8192, 16384, 32768) for d in (1, 2) for p in ("A", "B")}
    acc_r = {(u, d, p): 0.97 for u in (8192, 16384, 32768) for d in (1, 2) for p in ("A", "B")}
    assert calibrate.overload_u_p(acc_f, acc_r)["u_p"] == 16384
    assert calibrate.overload_u_p({k: 0.5 for k in acc_f}, acc_r)["action"] == calibrate.RETURN_TO_LEAD
    assert calibrate.overload_u_p(acc_f, {k: 0.9 for k in acc_r})["u_p"] is None
    assert calibrate.overload_u_p(acc_f, acc_r, unit=4)["u_p"] is None  # candidates scale with the unit


def test_calibration_snapshots() -> None:
    by = {c.label: calibrate.calibration_snapshots(c) for c in core.calibration_cells(True)}
    load4 = core.make_cell("CAL", "F-OQ", 8192, 4096, 1, 2191, run_updates=65536)
    assert calibrate.calibration_snapshots(load4)[-3:] == (32768, 49152, 65536) and 24576 in calibrate.calibration_snapshots(load4)
    assert len(by) == 50 and all(s for s in by.values())
    over = [c for c in core.overload_u_p_cells()]
    assert all(calibrate.calibration_snapshots(c) == (8192, 16384, 32768) for c in over)
    dense = next(c for c in core.dense_rate_cells() if c.slots == 16384)
    assert calibrate.calibration_snapshots(dense) == (8192, 32768)


def test_lane_l_status_labels_and_it_is_never_enabled_by_default() -> None:
    assert fz.lane_l_status(None) == fz.LANE_OMITTED_NO_INTERFACE == "OMITTED — no interface qualified before the freeze"
    for outcome in ("ADDRESSING-NOT-QUALIFIED", "INCONCLUSIVE", "ENGINEERING_FAIL", "INCOMPLETE", "NOT STARTED"):
        assert fz.lane_l_status(outcome, "A5-C", True) == fz.LANE_OMITTED_NO_INTERFACE
    assert fz.lane_l_status(fz.LANE_QUALIFIED_4096, "A5-C", True) == "OMITTED — QUALIFIED AT 4,096 ONLY"
    assert fz.lane_l_status(fz.LANE_QUALIFIED_BOTH, "A1", True) == "OMITTED — SUPERVISED ARM HAS NO 8K/4K CELL" == fz.lane_l_status(fz.LANE_QUALIFIED_BOTH, "A2", False)
    assert fz.lane_l_status(fz.LANE_QUALIFIED_BOTH, "A5-C", False) == "OMITTED — NOT OVERLOAD-QUALIFIED"
    assert fz.lane_l_status(fz.LANE_QUALIFIED_BOTH, "A5-C", True) == fz.LANE_WOULD_RUN
    assert core.Plan().lane_l is False and fz.Frozen().lane_status == fz.LANE_OMITTED_NO_INTERFACE and fz.Frozen().s0_status == "S0 NOT YET DECIDED"
