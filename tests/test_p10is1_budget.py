# ruff: noqa: E501
"""P10IS1 block budget and projection (ADR-0024 sections 15, 17.1 and ruling 24) on planted rates with answers derived BY HAND from the plan's lengths: B = (60 + H_c)/2, the base plan, levels granted to whole cells
in the fixed order, a cell closed at each level, a U0 of each ladder form, a long item that sets the makespan, and a base plan above the budget (which the freeze must refuse). Projections only: nothing here is measured."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from studies.p10is1 import budget, core  # noqa: E402

RATES_ALL = [(arm, n) for arm in core.ARMS for n in (256, 1024, 4096, 16384, 32768)]


def rates(r: float, workers: int = 1, contention: float = 1.0, evaluate: float = 0.0, fixed: float = 0.0) -> budget.Rates:
    return budget.Rates({k: r for k in RATES_ALL}, {k: evaluate for k in RATES_ALL}, contention, {"fixed": fixed}, workers)


def cells(u0: dict[str, int], granted: dict[str, int] | None = None, sat256: bool = True) -> list[dict]:  # type: ignore[type-arg]
    p = core.PlanParams({2048: 8192, 8192: 8192, 32768: 16384}, {u: 0.003 for u in core.units()}, u0, granted or {k: 4 * v for k, v in u0.items()}, sat256=sat256)
    return core.planned_cells(p, core.TEST)


U0 = {"2K/256": 98304, "8K/1K": 131072, "32K/4K": 131072}
# by hand (five replicates): not-ladder cells run 6 U_P (49,152 at rows 2,048 and 8,192, 98,304 at row 32,768), R2 runs U_P.
#   F-OQ, T-OQ, H8 at the five not-ladder cells: 4 x 49,152 + 98,304 = 294,912 each; D-OQ at four: 3 x 49,152 + 98,304 = 245,760; R2: 8,192 + 8,192 + 16,384 = 32,768
NOT_LADDER_PER_REPLICATE = 3 * 294_912 + 245_760 + 32_768  # 1,163,264
ONE_REPLICATE = NOT_LADDER_PER_REPLICATE + 2 * 4 * 131_072 + 98_304  # ladder cells at U0: 8K/1K and 32K/4K carry four arms each, 2K/256 one arm: 2,310,144
BASE_UPDATES = 5 * ONE_REPLICATE  # 11,550,720
BASE_ALL = BASE_UPDATES + ONE_REPLICATE  # plus the COUNTING REHEARSAL (section 17.1): every stage of one replicate on the rehearsal draw: 13,860,864


def test_base_plan_updates_by_hand() -> None:
    assert BASE_UPDATES == 11_550_720
    p = budget.project(cells(U0), U0, rates(1.0))
    assert p["train_seconds"] == BASE_UPDATES  # one worker, one second per update, no contention: the makespan is the sum


def test_budget_formula_and_makespan() -> None:
    assert budget.budget_hours(12.0) == 36.0 and budget.budget_hours(20.0) == 40.0 and budget.budget_hours(0.0) == 30.0
    assert budget.makespan([5, 4, 3, 3, 3], 2) == 10.0  # LPT by hand: A 5, B 4, B 7, A 8, B 10
    assert budget.makespan([100, 1, 1], 6) == 100.0  # never less than the longest item
    assert budget.makespan([], 3) == 0.0 and budget.makespan([7], 1) == 7.0
    assert budget.makespan([2, 2, 2, 2], 4) == 2.0 and budget.makespan([2, 2, 2, 2], 2) == 4.0
    with pytest.raises(ValueError):
        budget.makespan([1], 0)


def test_levels_granted_to_whole_cells_in_the_fixed_order_and_closed_cells_get_no_later_level() -> None:
    # H_c = 4 -> B = 32 h on the TOTAL (the hours already charged count). Rate chosen so that the base plan's remaining work is 26 h (total 30 h): r = 26 x 3600 / 11,550,720 s per update.
    r = 26 * 3600 / BASE_ALL
    out = budget.grant_levels(cells(U0), rates(r), 4.0)
    assert out["refused"] is False and out["budget_B_hours"] == 32.0 and abs(out["base_total_hours"] - 30.0) < 1e-9
    # by hand, in the fixed order (levels j = 1..4, cells 2K/256, 8K/1K, 32K/4K within a level), U0 = 98,304 / 131,072 / 131,072, five replicates:
    #   level 1: 2K/256 -> 131,072 adds 5 x 32,768 = 163,840 updates (0.369 h, total 30.37, granted); 8K/1K -> 196,608 adds 4 arms x 5 x 65,536 = 1,310,720 updates (2.95 h, total 33.3 > 32): closed; 32K/4K the same: closed
    #   level 2: 2K/256 -> 196,608 adds 5 x 98,304 = 491,520 updates in all (1.106 h, total 31.11): granted
    #   level 3: 2K/256 -> 262,144 adds 5 x 163,840 = 819,200 (1.844 h, total 31.84 <= 32): granted
    #   level 4: 2K/256 -> 393,216 adds 5 x 294,912 = 1,474,560 (3.32 h, total 33.3 > 32): closed
    assert out["grants"] == {"2K/256": 262144, "8K/1K": 131072, "32K/4K": 131072}
    assert [(x["level"], x["cell"], x["granted"]) for x in out["levels_considered"]] == [(1, "2K/256", True), (1, "8K/1K", False), (1, "32K/4K", False), (2, "2K/256", True), (3, "2K/256", True), (4, "2K/256", False)]
    assert out["closed"] == [{"cell": "8K/1K", "at_level": 1}, {"cell": "32K/4K", "at_level": 1}, {"cell": "2K/256", "at_level": 4}]  # a closed cell is not considered again at levels 2 to 4
    assert abs(out["total_hours"] - (30.0 + 1.2 * 819_200 * r / 3600.0)) < 1e-6  # five replicates plus the counting rehearsal's one: 6/5 of the extra updates and out["total_hours"] <= 32.0
    assert out["bound_at_4_u0_printed"] == {"2K/256": 393216, "8K/1K": 524288, "32K/4K": 524288}  # the projection's assumption is U0, with 4 x U0 printed beside it
    # a bigger budget grants more, in the same order: level 1 for all three cells comes before any level 2
    r_small = 10 * 3600 / BASE_ALL
    big = budget.grant_levels(cells(U0), rates(r_small), 20.0)
    assert [(x["level"], x["cell"]) for x in big["levels_considered"][:3]] == [(1, "2K/256"), (1, "8K/1K"), (1, "32K/4K")] and all(x["granted"] for x in big["levels_considered"][:3])
    assert big["grants"]["8K/1K"] >= 196608 and big["grants"]["32K/4K"] >= 196608


def test_a_whole_cell_is_costed_as_if_every_replicate_used_the_level() -> None:
    r = 30 * 3600 / BASE_UPDATES
    cs = cells(U0)
    one = budget.project(cs, {**U0, "8K/1K": 196608}, rates(r))["train_seconds"] - budget.project(cs, U0, rates(r))["train_seconds"]
    assert abs(one - 4 * 5 * 65536 * r) < 1e-6  # four arms x five replicates x 65,536 further updates


def test_u0_of_p10s1_form_and_of_the_power_of_two_form() -> None:
    p1s = {"2K/256": 393216, "8K/1K": 393216, "32K/4K": 786432}  # P10-S1's lengths: levels 1.333, 2, 2.667, 4 x U0
    c = cells(p1s)
    assert core.levels_above(393216) == [524288, 786432, 1048576, 1572864]
    out = budget.grant_levels(c, rates(1e-4), 12.0)  # tiny rates: everything fits, every cell reaches 4 x U0
    assert out["grants"] == {"2K/256": 1572864, "8K/1K": 1572864, "32K/4K": 3145728}
    p2 = {"2K/256": 131072, "8K/1K": 131072, "32K/4K": 262144}  # a power of two times 65,536: 1.5, 2, 3, 4 x U0
    out2 = budget.grant_levels(cells(p2), rates(1e-4), 12.0)
    assert out2["grants"] == {"2K/256": 524288, "8K/1K": 524288, "32K/4K": 1048576}


def test_base_plan_above_the_budget_is_refused() -> None:
    r = 28.5 * 3600 / BASE_ALL  # remaining 28.5 h + 4 h charged = 32.5 h against B = 32 h
    out = budget.grant_levels(cells(U0), rates(r), 4.0)
    assert out["refused"] is True and out["status"] == "BASE PLAN ABOVE BUDGET" and abs(out["total_hours"] - 32.5) < 1e-9 and out["grants"] == U0 and not out["levels_considered"]
    assert budget.grant_levels(cells(U0), rates(27.9 * 3600 / BASE_ALL), 4.0)["refused"] is False  # 31.9 h fits


def test_a_long_item_sets_the_makespan_and_can_close_a_cell() -> None:
    # six workers; every item 1e-3 s/update except T-OQ at 4,096 slots (the 32K/4K cell), 10 s/update: one such item at U0 = 131,072 is 1,310,720 s = 364 h on its own, above any budget
    tr = {k: 1e-3 for k in RATES_ALL}
    tr[("T-OQ", 4096)] = 10.0
    rt = budget.Rates(tr, {k: 0.0 for k in RATES_ALL}, 1.0, {}, 6)
    p = budget.project(cells(U0), U0, rt)
    assert p["train_seconds"] >= 131072 * 10.0 and p["longest_training_item_seconds"] == 131072 * 10.0
    assert budget.grant_levels(cells(U0), rt, 4.0)["refused"] is True  # the longest single cell alone is above B
    # with a tolerable long item the cell is closed at level 1 although the rest of the budget has room
    tr[("T-OQ", 4096)] = 0.2  # one T-OQ item at G is G x 0.2 s: 131,072 -> 7.3 h, 196,608 -> 10.9 h, 262,144 -> 14.6 h, 393,216 -> 21.8 h, 524,288 -> 29.1 h; the other cells add far less on the other five workers
    out = budget.grant_levels(cells(U0), budget.Rates(tr, {k: 0.0 for k in RATES_ALL}, 1.0, {}, 6), 4.0)
    # the longest item is run twice in sequence (the registered training stage, then the counting rehearsal's one replicate): total = 4 h charged + 2 x the item: level 1 (196,608): 4 + 21.8 = 25.8 h <= 32, granted;
    # level 2 (262,144): 4 + 29.1 = 33.1 h > 32: 32K/4K is closed at level 2 and keeps 196,608. 8K/1K (no long item) is not limited by it
    assert out["refused"] is False and out["grants"]["32K/4K"] == 196608 and {"cell": "32K/4K", "at_level": 2} in out["closed"]


def test_evaluation_and_fixed_stages_enter_the_projection() -> None:
    cs = cells(U0)
    r = rates(0.0, workers=1, evaluate=2.0, fixed=100.0)
    p = budget.project(cs, U0, r)
    snaps = sum(sum(1 for u in c["snapshots"] if u <= (U0[core.cell_name(c["facts"], c["slots"])] if c["ladder_cell"] else c["run"])) for c in cs)
    first = [c for c in cs if c["draw"] == 1]  # the counting rehearsal evaluates the snapshots of one replicate
    snaps1 = sum(sum(1 for u in c["snapshots"] if u <= (U0[core.cell_name(c["facts"], c["slots"])] if c["ladder_cell"] else c["run"])) for c in first)
    assert p["evaluate_seconds"] == 2.0 * snaps and p["fixed_seconds"] == 100.0 and p["counting_rehearsal_seconds"] == 2.0 * snaps1 and p["remaining_seconds"] == 2.0 * snaps + 2.0 * snaps1 + 100.0
    assert budget.Rates({}, {}, 1.0, {}, 1).contention == 1.0
    with pytest.raises(ValueError):
        budget.Rates({}, {}, 0.5, {}, 1)  # the contention ratio is at least 1


def test_the_contention_ratio_scales_training_only() -> None:
    cs = cells(U0)
    a = budget.project(cs, U0, rates(1e-3, workers=1, contention=1.0))
    b = budget.project(cs, U0, rates(1e-3, workers=1, contention=2.0))
    assert abs(b["train_seconds"] - 2 * a["train_seconds"]) < 1e-6 and b["evaluate_seconds"] == a["evaluate_seconds"]


def test_worker_choice_is_a_cost_rule_with_ties_to_the_smaller_count() -> None:
    cs = cells(U0)
    r6, r7 = rates(1e-3, workers=6, contention=1.9), rates(1e-3, workers=7, contention=2.5)
    out = budget.choose_workers({6: r6, 7: r7}, cs, U0)
    assert out["chosen_workers"] == min(out["projected_hours_by_workers"], key=lambda w: out["projected_hours_by_workers"][w])
    same = budget.choose_workers({6: rates(1e-3, workers=6), 7: rates(1e-3, workers=6)}, cs, U0)
    assert same["chosen_workers"] == 6


def test_caps_from_projection() -> None:
    caps = budget.caps_from_projection(12.0, {"train": 20.0, "evaluate": 3.2})
    assert caps["total_cap_hours"] == 59.0  # 12 + 2 x 23.2 = 58.4 -> 59
    assert caps["stage_cap_hours"] == {"train": 40.0, "evaluate": 7.0} and not caps["total_above_limit"]
    assert budget.caps_from_projection(30.0, {"train": 20.0})["total_above_limit"] is True  # 70 > 60: the human lead's own decision, not the delegation's
    # B guarantees it: with the remaining at the limit B - H_c the cap is at most 60
    h_c = 12.0
    rem = budget.budget_hours(h_c) - h_c
    assert budget.caps_from_projection(h_c, {"x": rem})["total_cap_hours"] <= 60.0
