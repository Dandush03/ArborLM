# ruff: noqa: E501
"""P10S1 revision 5 budget (ADR-0021 sections 10.1 item 0a and 10.3; brief group 12): the contention ratio c, C_need and the cap rule, longest-first packing, the three cuts in their fixed order,
NOT STARTED: BUDGET above C_max, the item projections and caps of the timing preview, the frozen round trip and the cap table of the twelve configurations. Pure functions on constructed numbers;
the cost fixtures never set the 1,024-slot cost equal to the 4,096-slot cost (review m10). Self-check only: not independent review, not Astra validation, not human approval."""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from studies.p10s1 import budget, calibrate, core  # noqa: E402
from studies.p10s1 import classes as C  # noqa: E402
from studies.p10s1 import frozen as fz  # noqa: E402

GIB = 1024**3
CPU = fz.default_cpu_table()


def make_rates(spu: float = 0.01, evaluation: float = 5.0, overhead: float = 2.0, peak: int = int(0.7 * GIB)) -> budget.Rates:
    return {i: budget.Rate(spu * (1 + core.work_formula("F-OQ" if i[0] == "D-OQ" else i[0], i[2])["W"] / 1e5), evaluation, overhead, peak, peak, peak, peak) for i in budget.rehearsal_items(core.Plan())}


def test_rehearsal_items_cover_the_31_configurations() -> None:
    items = budget.rehearsal_items()
    assert len(items) == 31 and len(set(items)) == 31 and ("F-OQ", 2048, 256) in items and ("R2", 32768, 32768) in items
    assert len(budget.rehearsal_items(core.Plan(sat256=False))) == 30
    assert len(budget.rehearsal_items(core.Plan(dense_cut=("8K/16K",)))) == 31  # the rehearsal runs every configuration before any cut
    for i in items:
        assert budget.parse_item_label(budget.item_label(i)) == i


def test_the_contention_ratio_is_the_largest_ratio_and_never_below_one() -> None:
    iso = {("F-OQ", 4096): 0.010, ("T-OQ", 1024): 0.004, ("D-OQ", 16384): 0.020}
    six = {("F-OQ", 4096): 0.0093, ("T-OQ", 1024): 0.0052, ("D-OQ", 16384): 0.0235}
    r = budget.contention_ratio(six, iso)
    assert r["c"] == pytest.approx(0.0052 / 0.004) and r["worst"] == "T-OQ|1024" and r["ratios"]["F-OQ|4096"] == pytest.approx(0.93)
    below = budget.contention_ratio({("F-OQ", 4096): 0.0093}, iso)
    assert below["c"] == 1.0 and below["ratios"]["F-OQ|4096"] < 1.0  # never below 1.0
    unmatched = budget.contention_ratio({("F-OQ", 256): 0.01}, iso)
    assert unmatched["c"] == 1.0 and unmatched["unmatched"] == ["F-OQ|256"]
    assert budget.contention_ratio({}, iso)["c"] == 1.0


def test_c_scales_the_training_projection_from_the_isolated_rates_and_longest_first_packing() -> None:
    plan = core.Plan(seed_block_draws=())
    fro = fz.Frozen.build(plan, CPU)
    rates = make_rates(overhead=0.0)
    iso = {(a, n): 0.005 + 1e-9 * core.work_formula(a, n)["W"] * 100 for a, ns in core.arm_slot_counts().items() for n in ns}
    p1 = budget.stage_projection(plan, rates, fro, isolated=iso, c=1.0)
    p2 = budget.stage_projection(plan, rates, fro, isolated=iso, c=2.0)
    assert p2.training_seconds == pytest.approx(2.0 * p1.training_seconds, rel=0.05) and p2.evaluation_seconds == p1.evaluation_seconds
    cells = core.registered_cells(plan)
    jobs = [budget.cell_training_seconds(x, rates, iso, 1.0) for x in cells]
    assert p1.training_seconds == pytest.approx(budget.makespan(jobs, 6)) and p1.training_seconds >= sum(jobs) / 6 and p1.training_seconds >= max(jobs)
    assert budget.makespan([10.0, 9.0, 8.0, 1.0, 1.0, 1.0], 2) == 17.0  # longest first
    assert budget.makespan([1.0] * 6 + [6.0], 6) == 6.0 or budget.makespan([1.0] * 6 + [6.0], 6) == 7.0


def test_c_need_the_cap_rule_and_the_ceiling() -> None:
    cap_max = core.load_config()["resources"]["cap_max_hours"] * 3600.0  # from the config, never typed
    h = budget.headroom_rule(1.57 * 3600, 5.0 * 3600, cap_max)  # C_need = charged + 2 x remaining
    assert h.required_seconds == pytest.approx((1.57 + 10.0) * 3600) and h.ok and h.cap_hours == math.ceil(11.57)
    exact = budget.headroom_rule(0.0, cap_max / 2.0, cap_max)
    assert exact.ok and exact.required_seconds == pytest.approx(cap_max) and exact.cap_hours == int(cap_max / 3600.0)
    over = budget.headroom_rule(0.0, cap_max / 2.0 + 1.0, cap_max)
    assert not over.ok and over.cap_hours is None and over.shortfall_seconds == pytest.approx(2.0)
    assert not budget.headroom_rule(0.0, math.inf, cap_max).ok
    assert budget.headroom_rule(3600.0, 3600.0, cap_max).cap_hours == 3  # 1 h + 2 x 1 h = 3 h: rounded up to the whole hour, not to a typed figure
    assert budget.headroom_rule(3601.0, 3600.0, cap_max).cap_hours == 3 + 1 - 0 or budget.headroom_rule(3601.0, 3600.0, cap_max).cap_hours == 4


def test_the_three_cuts_in_their_fixed_order_and_nothing_else() -> None:
    seq = budget.cut_sequence()
    assert [p.seed_block_draws for p, _ in seq] == [(1, 2), (1,), (), ()] and [p.dense_cut for p, _ in seq] == [(), (), (), ("8K/16K",)]
    assert [c for _p, c in seq][1] == ["cut 1: the seed block on draw 2"] and seq[3][1][-1] == "cut 3: D-OQ at 8K/16K" and len(seq) == 4  # no other cut exists
    base = core.Plan(row_u_p=(8192, 8192, 16384), u_l=(131072, 393216), sat256=False)
    assert all(p.row_u_p == base.row_u_p and p.u_l == base.u_l and not p.sat256 for p, _ in budget.cut_sequence(base))
    assert all(p.unit == 16 for p, _ in budget.cut_sequence(core.Plan(unit=16)))


def choose(spu: float, *, charged: float, cap_max: float, peak: int = int(0.7 * GIB), base: core.Plan | None = None) -> budget.CutResult:
    rates = make_rates(spu=spu, peak=peak)
    slow = ("D-OQ", 8192, 16384)  # the one cell cut 3 removes dominates the packing, so that the cut changes C_need
    rates[slow] = budget.Rate(5.0, 5.0, 2.0, peak, peak, peak, peak)
    return budget.choose_plan(rates, budget.Fixed(60.0, 300.0, 60.0, 30.0, 30.0), CPU, charged_seconds=charged, cap_max_seconds=cap_max, base=base)


def test_choose_plan_applies_the_cuts_in_order_and_not_started_budget_above_the_ceiling() -> None:
    cap_max = core.load_config()["resources"]["cap_max_hours"] * 3600.0
    easy = choose(0.0005, charged=3000.0, cap_max=1e12)
    assert easy.ok and easy.applied_cuts == [] and easy.plan == core.Plan((1, 2)) and easy.headroom is not None and easy.headroom.cap_hours is not None
    required = [t["required_seconds"] for t in choose(0.0005, charged=3000.0, cap_max=1e12).tried]
    full = choose(0.0005, charged=3000.0, cap_max=1e12)
    assert full.ok and len(full.tried) == 1
    needs = [t["required_seconds"] for t in choose(0.0005, charged=3000.0, cap_max=1.0).tried]  # C_need of the four plans of the cut sequence, in order
    assert len(needs) == 4 and needs[0] >= needs[1] >= needs[2] > needs[3] and required[0] == pytest.approx(needs[0])
    mid = choose(0.0005, charged=3000.0, cap_max=(needs[0] + needs[1]) / 2.0)  # draw 2's seed block does not fit: cut 1, nothing else
    assert mid.ok and mid.applied_cuts == ["cut 1: the seed block on draw 2"] and mid.plan is not None and mid.plan.seed_block_draws == (1,) and [t["ok"] for t in mid.tried] == [False, True]
    deep = choose(0.0005, charged=3000.0, cap_max=(needs[2] + needs[3]) / 2.0)  # only cut 3 (D-OQ at 8K/16K) makes it fit
    assert deep.ok and deep.applied_cuts[-1] == "cut 3: D-OQ at 8K/16K" and deep.plan is not None and deep.plan.dense_cut == ("8K/16K",)
    nope = choose(0.0005, charged=3000.0, cap_max=needs[3] * 0.5)  # still above C_max after the last cut: NOT STARTED: BUDGET, returns to the human lead
    assert not nope.ok and nope.plan is None and nope.returns_to_lead is not None and budget.NOT_STARTED_BUDGET in nope.returns_to_lead and len(nope.tried) == 4
    big_charged = choose(0.0005, charged=cap_max + 1.0, cap_max=cap_max)
    assert not big_charged.ok and budget.NOT_STARTED_BUDGET in str(big_charged.returns_to_lead)
    mem = choose(0.0005, charged=3000.0, cap_max=cap_max, peak=int(1.6 * GIB))
    assert not mem.ok and mem.returns_to_lead is not None and "memory" in mem.returns_to_lead


def test_item_projections_and_caps_of_the_timing_preview() -> None:
    wall = {(a, n): 0.01 * (1 + n / 4096) for a, ns in core.arm_slot_counts().items() for n in ns}
    proj = budget.item_projection(wall)
    assert set(proj) == {"load", "row-up", "h8", "dense", "load-ext"} and [proj[i]["runs"] for i in ("load", "row-up", "h8", "dense", "load-ext")] == [10, 12, 8, 40, 8]
    for item, p in proj.items():
        assert p["cap_seconds"] == pytest.approx(2.0 * p["projected_wall_seconds"]) and p["missing_rates"] == []  # twice the projected wall time at six workers
    longest = max(262144 * wall[("T-OQ", 1024)], 524288 * wall[("F-OQ", 4096)], 524288 * wall[("T-OQ", 4096)])
    assert proj["load"]["projected_wall_seconds"] >= longest  # no item is shorter than its longest run
    partial = budget.item_projection({k: v for k, v in wall.items() if k != ("T-OQ", 1024)})
    assert partial["load"]["cap_seconds"] is None and partial["load"]["missing_rates"] == ["T-OQ|1024"] and partial["row-up"]["cap_seconds"] is None and partial["h8"]["cap_seconds"] is not None  # nothing in the pooled stage starts on an assumed cost
    rows = {2048: 8192, 8192: 8192, 32768: 8192}
    assert budget.item_projection(wall, row_u_p=rows)["dense"]["projected_wall_seconds"] <= proj["dense"]["projected_wall_seconds"]  # items 2 and 3 are projected at the largest candidate before item 1 fixes the rows


def test_frozen_round_trip_the_caps_table_and_the_calibration_snapshots() -> None:
    plan = core.Plan(row_u_p=(8192, 8192, 16384), u_l=(131072, 393216), toq_not_loaded=("32K/4K",))
    rates = {"4096": 0.01, "16384": 0.03, "8K/1K": 0.003, "32K/4K": 0.01}
    fro = fz.Frozen.build(plan, CPU, dense_rates=rates, h8_undertrained=["8K/4K"], cuts=["cut 1: x"])
    again = fz.Frozen.from_json(fro.as_json())
    assert again.as_json() == fro.as_json() and again.plan == plan and again.dense_rates == rates
    lrs = {c.label: c.lr for c in core.registered_cells(plan, dense_rates=rates) if c.arm == "D-OQ" and c.draw == 1}
    assert {core.parse_label(label).name: lr for label, lr in lrs.items()} == {"2K/4K": 0.01, "8K/4K": 0.01, "8K/16K": 0.03, "32K/16K": 0.03, "8K/1K": 0.003, "32K/4K": 0.01}  # looked up by unit, not by slot count
    cell = next(c for c in core.registered_cells(plan) if c.arm == "F-OQ" and (c.facts, c.slots) == (32768, 4096) and c.draw == 1)
    snaps = fro.snapshots(cell)
    assert {32768, 49152, 65536, 131072, 196608, 262144, 393216} <= set(snaps) and max(snaps) == 393216 and snaps == tuple(sorted(set(snaps)))
    for cand in core.load_candidates("32K/4K"):
        if cand <= 393216:
            assert cand // 2 in snaps  # every candidate's half is a snapshot
    table = budget.caps_table(make_rates(), budget.Fixed(60.0, 300.0, 60.0, 30.0, 30.0), CPU, base=plan)
    assert len(table["configurations"]) == 12 and set(table["configurations"]) == {p.key() for p in core.plan_configurations(plan)}
    for p in core.plan_configurations(plan):
        assert budget.cap_for(table, "train", p) > 0 and budget.cap_for(table, "evaluate", p) > 0
    with pytest.raises(budget.CapMissing):
        budget.cap_for(table, "train", core.Plan(seed_block_draws=(), unit=16))
    cal_cell = next(c for c in core.load_search_cells() if c.arm == "F-OQ" and c.slots == 1024 and c.draw == 1)
    first = core.first_search_candidates("8K/1K")  # the first search's cell (ceiling 262,144) is read at its own five candidates (section 25.15)
    assert calibrate.calibration_snapshots(cal_cell) == tuple(sorted({512 * 2**k for k in range(0, 10)} | set(first) | {c // 2 for c in first}))
    dense = next(c for c in core.dense_rate_cells({2048: 8192, 8192: 8192, 32768: 8192}) if c.slots == 1024 and c.lr == 0.1 and c.draw == 1)
    assert calibrate.calibration_snapshots(dense) == (4096, 8192, 16384, 32768, 65536)  # readout / 2^k for the tie walk
    assert calibrate.calibration_snapshots(next(c for c in core.row_u_p_cells() if c.arm == "R2" and c.draw == 1 and c.facts == 2048)) == (8192, 16384, 32768)
    assert C.MC_AMBIGUOUS == "MC-AMBIGUOUS"


def test_work_and_multiply_add_formulas_hold_at_256_and_1024_slots() -> None:
    assert fz.trainable_parameters("F-OQ", 256) == core.foq_trainable_parameters(256) and fz.trainable_parameters("R2", 32768) == 32768 * 32 + 1025
    assert fz.analytic_madds_per_update("F-OQ", 256) < fz.analytic_madds_per_update("F-OQ", 1024) < fz.analytic_madds_per_update("F-OQ", 4096)
    assert fz.memory_madds("T-OQ", 1024) == 2 * 128 * ((1024 // 256) * 16 + 512 * 16) + 3 * 128 * 32 * 32 and fz.analytic_madds_per_update("D-OQ", 1024) > fz.analytic_madds_per_update("F-OQ", 1024)
    for arm in ("T-OQ", "H8", "D-OQ"):
        with pytest.raises(ValueError):
            fz.analytic_madds_per_update(arm, 256)
    assert set(fz.default_cpu_table()) == {(a, n) for a, ns in core.arm_slot_counts().items() for n in ns} and ("F-OQ", 256) in fz.default_cpu_table() and ("R2", 32768) in fz.default_cpu_table()
