# ruff: noqa: E501
"""P10IS1 calibration rules (ADR-0024 section 7): the equal rate search and its edge rule, the fixed order of selections and U_P, the ladder search with its ceilings and registered outcomes, H8's annotations. A table engine
answers with designed figures; the expected selections, orders and outcomes are derived by hand from the design. Self-check only."""

import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from studies.p10is1 import calibrate as K  # noqa: E402
from studies.p10is1 import core  # noqa: E402

RR = K.RateRun
GRID = [0.001, 0.003, 0.01, 0.03, 0.1]


def run(v: float, walk: dict[int, float] | None = None, diverged: bool = False) -> K.RateRun:
    return RR(v, v, walk or {}, diverged)


def results(vals: dict[float, float], **kw: Any) -> dict[float, K.RateRun]:
    return {r: run(v, **kw) for r, v in vals.items()}


def test_selection_highest_minimum_a_use_in_the_middle_of_the_grid() -> None:
    sel = K.select_rate(results({0.001: 0.5, 0.003: 0.7, 0.01: 0.9, 0.03: 0.8, 0.1: 0.6}), GRID, 0, 8192)
    assert sel["action"] == K.SELECTED and sel["rate"] == 0.01 and sel["decided_by"] == "readout a_use" and sel["edge"] is None


def test_tie_walk_faster_learner_then_smaller_rate_and_missing_walk() -> None:
    # 0.01 and 0.03 within 0.02 at the readout (0.90, 0.89): the walk reads readout/2: 0.85 against 0.80: only 0.01 is within 0.02 of the best there -> 0.01 (the faster learner)
    v = {0.001: run(0.5), 0.003: run(0.6), 0.01: run(0.90, {4096: 0.85, 2048: 0.5, 1024: 0.3, 512: 0.1}), 0.03: run(0.89, {4096: 0.80, 2048: 0.5, 1024: 0.3, 512: 0.1}), 0.1: run(0.7)}
    sel = K.select_rate(v, GRID, 0, 8192)
    assert sel["rate"] == 0.01 and sel["decided_by"] == "faster learner: a_use at 4096"
    # nothing separates them by 0.02 at any snapshot: the smaller rate
    same = {0.001: run(0.5), 0.003: run(0.6), 0.01: run(0.90, {4096: 0.85, 2048: 0.5, 1024: 0.3, 512: 0.1}), 0.03: run(0.89, {4096: 0.86, 2048: 0.51, 1024: 0.31, 512: 0.11}), 0.1: run(0.7)}
    sel2 = K.select_rate(same, GRID, 0, 8192)
    assert sel2["rate"] == 0.01 and "smaller learning rate" in sel2["decided_by"]
    with pytest.raises(K.TieNeedsLead):
        K.select_rate({**same, 0.01: run(0.90), 0.03: run(0.89)}, GRID, 0, 8192)
    assert K.tie_snapshots(8192) == (4096, 2048, 1024, 512) and K.tie_snapshots(16384) == (8192, 4096, 2048, 1024)


def test_edge_rule_extends_one_step_at_most_twice_in_total_then_rate_at_edge() -> None:
    top = results({0.001: 0.3, 0.003: 0.4, 0.01: 0.5, 0.03: 0.6, 0.1: 0.7})  # the best is the top rate by 0.1 > 0.02
    sel = K.select_rate(top, GRID, 0, 8192)
    assert sel["action"] == K.EXTEND and sel["direction"] == "up" and sel["new_rate"] == 0.3
    sel2 = K.select_rate({**top, 0.3: run(0.8)}, [*GRID, 0.3], 1, 8192)
    assert sel2["action"] == K.EXTEND and sel2["new_rate"] == 1.0  # the second step, the grid now holds one extension upward
    sel3 = K.select_rate({**top, 0.3: run(0.8), 1.0: run(0.9)}, [*GRID, 0.3, 1.0], 2, 8192)
    assert sel3["action"] == K.RATE_AT_EDGE and "returns to the human lead" in sel3["reason"]
    bottom = results({0.001: 0.9, 0.003: 0.7, 0.01: 0.5, 0.03: 0.4, 0.1: 0.3})
    assert K.select_rate(bottom, GRID, 0, 8192)["new_rate"] == 0.0003 and K.select_rate(bottom, GRID, 0, 8192)["direction"] == "down"
    # the two extensions are two in TOTAL across directions and selections: one used (upwards) leaves one for the other direction
    assert K.select_rate(bottom, GRID, 1, 8192)["action"] == K.EXTEND and K.select_rate(bottom, GRID, 2, 8192)["action"] == K.RATE_AT_EDGE
    only_one = K.select_rate({0.1: run(0.9)}, [0.1], 0, 8192)
    assert only_one["action"] == K.EXTEND  # a single live rate is the best by more than 0.02 (the rest diverged)


def test_a_best_rate_at_the_edge_chosen_by_the_tie_walk_is_taken_and_recorded() -> None:
    v = {0.001: run(0.3), 0.003: run(0.4), 0.01: run(0.5), 0.03: run(0.89, {4096: 0.80, 2048: 0.5, 1024: 0.3, 512: 0.1}), 0.1: run(0.90, {4096: 0.86, 2048: 0.6, 1024: 0.4, 512: 0.2})}  # 0.1 and 0.03 within 0.02
    sel = K.select_rate(v, GRID, 0, 8192)
    assert sel["action"] == K.SELECTED and sel["rate"] == 0.1 and sel["edge"] == "EDGE BY TIE-WALK" and sel["grid"] == GRID  # not extended


def test_a_diverged_rate_is_kept_and_left_out_and_all_diverged_returns() -> None:
    v = {0.001: run(0.5), 0.003: run(0.7), 0.01: run(0.95, diverged=True), 0.03: run(0.8), 0.1: run(0.6)}
    sel = K.select_rate(v, GRID, 0, 8192)
    assert sel["rate"] == 0.03 and sel["diverged"] == [0.01]  # 0.95 is a diverged run (e.g. a raw count inside the chance interval): never selected
    assert K.select_rate({r: run(0.0, diverged=True) for r in GRID}, GRID, 0, 8192)["action"] == K.RETURN_ALL_DIVERGED


def test_search_unit_extends_by_measuring_the_new_rate_and_carries_the_count() -> None:
    table = {0.001: 0.3, 0.003: 0.4, 0.01: 0.5, 0.03: 0.6, 0.1: 0.7, 0.3: 0.75}  # 0.3 beats 0.1 by 0.05 > 0.02: extend again to 1.0; 1.0 is worse -> 0.3 selected after two extensions? no: 0.3 is not at the end once 1.0 is in
    table[1.0] = 0.5
    calls: list[tuple[str, float, int]] = []

    def measure(unit: str, rate: float, readout: int) -> K.RateRun:
        calls.append((unit, rate, readout))
        return run(table[rate])

    state: dict[str, Any] = {}
    sel = K.search_unit(measure, "F-OQ|1024", 8192, state)
    assert sel["rate"] == 0.3 and state["extensions"] == 2 and state["grid"] == [0.001, 0.003, 0.01, 0.03, 0.1, 0.3, 1.0]
    assert [c[1] for c in calls] == [0.001, 0.003, 0.01, 0.03, 0.1, 0.3, 1.0]  # each rate measured once, in the order the edge rule asked for them
    # the re-selection reuses the extended grid and has no extension left
    calls.clear()
    table2 = {r: 0.1 for r in table} | {1.0: 0.9}
    sel2 = K.search_unit(lambda u, r, ro: run(table2[r]), "F-OQ|1024", 16384, state)
    assert sel2["action"] == K.RATE_AT_EDGE and state["extensions"] == 2  # 1.0 is the best by more than 0.02 and no extension is left


def test_u_p_of_row() -> None:
    def views(vals: dict[int, float]) -> K.Views:
        return {u: {(d, p): a for d in (1, 2) for p in "AB"} for u, a in vals.items()}

    foq = views({8192: 0.85, 16384: 0.91, 32768: 0.95, 65536: 0.97})
    r2 = views({8192: 0.96, 16384: 0.94, 32768: 0.96, 65536: 0.97})
    assert K.u_p_of_row(foq, r2)["u_p"] == 32768  # 16,384 fails on R2 (0.94 < 0.95), 8,192 on F-OQ (0.85 < 0.90)
    foq2 = {**foq, 32768: {(1, "A"): 0.95, (1, "B"): 0.95, (2, "A"): 0.95, (2, "B"): 0.89}}
    assert K.u_p_of_row(foq2, r2)["u_p"] == 65536  # one view below 0.90 at 32,768 on the second draw, panel B
    low = views({8192: 0.1, 16384: 0.2, 32768: 0.3, 65536: 0.89})
    res = K.u_p_of_row(low, r2)
    assert res["u_p"] is None and res["action"] == "RETURN TO THE HUMAN LEAD"  # no other value is substituted


def series(final: float, hit: int, upto: int) -> dict[int, float]:
    pts = core.ladder_points(upto)
    marks = {p for q in pts for p in (q, q // 2)}
    return {u: min(final, final * u / hit) for u in sorted(marks)}


def views4(final: float, hit: int, upto: int) -> dict[tuple[int, str], dict[int, float]]:
    return {(d, p): series(final, hit, upto) for d in (1, 2) for p in "AB"}


def test_arm_calibrated_length_two_consecutive_ladder_points_and_the_4_bits_condition() -> None:
    # flat from 32,768 on: i* gains nothing from 32,768 to 65,536; the first ladder point 65,536 cannot be the answer (it has no predecessor): the answer is the second, 98,304
    assert K.arm_calibrated_length(views4(2.0, 30000, 1572864), 1572864) == 98304
    # still rising until 200,000 updates (i = 2.0 x u / 200,000): the gain over the last doubling falls to 0.10 only late; the plateau test at u needs i*(u) - i*(u/2) <= 0.10
    slow = K.arm_calibrated_length(views4(3.0, 400000, 1572864), 1572864)
    assert slow is not None and slow >= 524288
    # a view above 4.0 bits is NOT full in the calibration (although it plateaus)
    assert K.arm_calibrated_length(views4(4.2, 30000, 1572864), 1572864) is None
    # not full at the ceiling: None; fewer than four views: None
    assert K.arm_calibrated_length(views4(3.0, 5_000_000, 1572864), 1572864) is None
    assert K.arm_calibrated_length({k: v for k, v in list(views4(2.0, 30000, 1572864).items())[:3]}, 1572864) is None
    assert K.ladder_ceiling("8K/1K") == 1572864 and K.ladder_ceiling("2K/256") == 1572864 and K.ladder_ceiling("32K/4K") == 3145728


def test_registered_outcomes_on_reaching_the_ceiling() -> None:
    o = K.cell_outcome("2K/256", None, None)
    assert o["action"] == "NOT RUN" and not o["runs"] and o["note"] == "256 NOT MEASURED — NOT FULL WITHIN CEILING" and not o["returns_to_lead"]
    assert K.cell_outcome("2K/256", 131072, None)["u0"] == 131072 and K.cell_outcome("2K/256", 131072, None)["runs"]
    both = K.cell_outcome("8K/1K", 262144, 393216)
    assert both["u0"] == 393216 and not both["toq_predicted_not_full"]  # the larger of the two
    t = K.cell_outcome("32K/4K", 786432, None)
    assert t["u0"] == 786432 and t["toq_predicted_not_full"] and t["note"] == "T-OQ PREDICTED NOT FULL AT 32K/4K" and not t["returns_to_lead"]
    f = K.cell_outcome("8K/1K", None, 262144)  # F-OQ not full: returns to the lead even though T-OQ is full
    assert f["returns_to_lead"] and f["action"] == "RETURN TO THE HUMAN LEAD" and "no load, ceiling or arm changes" in f["options"]
    assert K.cell_outcome("8K/1K", None, None)["toq_predicted_not_full"] is True


def test_h8_annotations() -> None:
    rep = K.h8_report({"2K/1K": 0.95, "8K/4K": 0.88, "32K/16K": 0.91, "2K/4K": 0.90, "8K/16K": 0.899}, [core.cell_name(f, n) for f, n in core.arm_cells("H8")])
    assert rep["undertrained_cells"] == ["8K/16K", "8K/4K"]
    assert rep["annotations"] == {"8K/1K": "H8 NOT CALIBRATED AT U_P AT 8K/1K", "8K/4K": "UNDERTRAINED-AT-U_P", "8K/16K": "UNDERTRAINED-AT-U_P", "32K/4K": "H8 NOT CALIBRATED AT U_P AT 32K/4K"}
    # 0.90 exactly is not below 0.90


class TableEngine:
    """Designed answers: every unit peaks at 0.01 (a_use 0.9, 0.1 below its neighbours); U_P candidates by row; ladder curves by cell and arm."""

    def __init__(self, u_p_foq: dict[int, int], ladder: dict[tuple[str, str], tuple[float, int]] | None = None, best: Mapping[str, float] | None = None, h8_extra: Mapping[str, float] | None = None) -> None:
        self.u_p_foq, self.best = u_p_foq, dict(best or {})
        self.ladder = ladder or {}
        self.calls: list[tuple[str, str, Any]] = []
        self.extra = h8_extra or {"2K/4K": 0.95, "8K/16K": 0.95}

    def measure(self, unit: str, rate: float, readout: int) -> K.RateRun:
        self.calls.append(("measure", unit, (rate, readout)))
        peak = self.best.get(unit, 0.01)
        gap = abs(GRID_ORDER.index(rate) - GRID_ORDER.index(peak)) if rate in GRID_ORDER and peak in GRID_ORDER else 5
        a = max(0.0, 0.9 - 0.1 * gap)
        return K.RateRun(a, a, {readout // d: a - 0.01 * d for d in (2, 4, 8, 16)}, False)

    def row_up(self, row: int, foq_rate: float, r2_rate: float) -> tuple[K.Views, K.Views]:
        self.calls.append(("row_up", str(row), (foq_rate, r2_rate)))
        u_p = self.u_p_foq[row]
        cands = (8192, 16384, 32768, 65536)
        foq = {u: {(d, p): (0.92 if u >= u_p else 0.5) for d in (1, 2) for p in "AB"} for u in cands}
        r2 = {u: {(d, p): 0.97 for d in (1, 2) for p in "AB"} for u in cands}
        return foq, r2

    def ladder_views(self, name: str, arm: str, rate: float, ceiling: int) -> dict[tuple[int, str], dict[int, float]]:
        self.calls.append(("ladder", name, (arm, rate, ceiling)))
        final, hit = self.ladder[(name, arm)]
        return views4(final, hit, ceiling)

    def h8_extra(self, unit_rate: Mapping[str, float]) -> Mapping[str, float]:
        self.calls.append(("h8_extra", "H8", dict(unit_rate)))
        return self.extra


GRID_ORDER = [0.001, 0.003, 0.01, 0.03, 0.1]
LADDER_OK = {("2K/256", "F-OQ"): (1.0, 30000), ("8K/1K", "F-OQ"): (1.5, 30000), ("8K/1K", "T-OQ"): (1.4, 30000), ("32K/4K", "F-OQ"): (1.5, 60000), ("32K/4K", "T-OQ"): (1.4, 400000)}


def test_the_fixed_order_of_rates_and_u_p() -> None:
    eng = TableEngine({2048: 16384, 8192: 8192, 32768: 32768}, LADDER_OK)
    cal = K.run_calibration(eng)
    assert not cal.returns_to_lead and cal.row_u_p == {2048: 16384, 8192: 8192, 32768: 32768}
    # by hand: 14 units that are not loaded are selected first at their row's provisional readout (8,192 / 8,192 / 16,384 by the unit's selection-cell row), then U_P per row (three row_up calls: U_P is computed once),
    # then the units whose selection cell lies in a row whose U_P differs from its provisional readout are selected once more at U_P: row 2,048 (U_P 16,384 against 8,192): F-OQ, T-OQ, H8 at 1,024 slots and R2 at 2K/4K;
    # row 32,768 (32,768 against 16,384): F-OQ, T-OQ, H8, D-OQ at 16,384 slots and R2 at 32K/32K; row 8,192 (8,192 against 8,192): none. The nine loaded-cell units are selected last, at 65,536.
    order = [c for c in cal.order]
    sel_at = [(o.split()[1], int(o.split()[-1])) for o in order if o.startswith("select")]
    plain_first = sel_at[:14]
    prov = {"1024": 8192, "4096": 8192, "16384": 16384, "2K/4K": 8192, "8K/16K": 8192, "32K/32K": 16384}
    assert all(r == prov[u.split("|")[1]] for u, r in plain_first) and len({u for u, _ in plain_first}) == 14
    u_p_lines = [k for k, o in enumerate(order) if o.startswith("U_P of row")]
    assert u_p_lines == [14, 15, 16]
    resel = sel_at[14:14 + 9]
    assert sorted(resel) == sorted([("F-OQ|1024", 16384), ("T-OQ|1024", 16384), ("H8|1024", 16384), ("R2|2K/4K", 16384), ("F-OQ|16384", 32768), ("T-OQ|16384", 32768), ("H8|16384", 32768), ("D-OQ|16384", 32768), ("R2|32K/32K", 32768)])
    loaded_last = sel_at[14 + 9 + 0 :]
    # between the U_P lines and the re-selections sit the three U_P lines; the loaded units follow the re-selections
    assert len(loaded_last) == 9 and all(r == 65536 and "/" in u.split("|")[1] and u.split("|")[1] not in ("2K/4K", "8K/16K", "32K/32K") for u, r in loaded_last)
    assert sum(1 for c in eng.calls if c[0] == "row_up") == 3
    assert [len(v) for u, v in cal.selections.items() if u in ("F-OQ|1024", "F-OQ|4096", "F-OQ|8K/1K")] == [2, 1, 1]
    assert cal.rates["F-OQ|1024"] == 0.01 and cal.rates["D-OQ|8K/1K"] == 0.01
    # the order of the calls: every 'measure' with a readout of 65,536 comes after every other 'measure'; the ladder runs come after all selections
    kinds = [c[0] for c in eng.calls]
    assert kinds.index("ladder") > max(i for i, k in enumerate(kinds) if k == "measure")
    meas = [c[2][1] for c in eng.calls if c[0] == "measure"]
    first65 = meas.index(65536)
    assert all(m == 65536 for m in meas[first65:]) and 65536 not in meas[:first65]


def test_u0_of_each_ladder_cell_and_the_record() -> None:
    eng = TableEngine({2048: 8192, 8192: 8192, 32768: 16384}, LADDER_OK)
    cal = K.run_calibration(eng)
    rec = K.to_record(cal)
    # F-OQ flat from 30,000 -> 98,304; T-OQ at 32K/4K rises until 400,000: F-OQ's 32K/4K (60,000 hit -> 98,304) against T-OQ's later length: U0 is the larger
    assert rec["u0"]["2K/256"] == 98304 and rec["u0"]["8K/1K"] == 98304
    assert rec["u0"]["32K/4K"] == cal.ladder["32K/4K"]["toq_length"] and cal.ladder["32K/4K"]["toq_length"] > 98304
    assert rec["sat256"] is True and rec["complete"] is True and rec["row_u_p"] == {"2048": 8192, "8192": 8192, "32768": 16384}
    assert cal.h8["annotations"] == {"8K/1K": "H8 NOT CALIBRATED AT U_P AT 8K/1K", "32K/4K": "H8 NOT CALIBRATED AT U_P AT 32K/4K"}  # H8 reaches 0.9 at every calibrated cell; the loaded cells are not calibrated at U_P
    # re-selections do not happen when every U_P equals its provisional readout
    assert all(len(v) == 1 for v in cal.selections.values())


def test_calibration_returns_to_the_lead_on_edge_no_u_p_and_f_oq_not_full() -> None:
    edge = K.run_calibration(TableEngine({2048: 8192, 8192: 8192, 32768: 16384}, LADDER_OK, best={"F-OQ|1024": 0.1}))
    assert not edge.returns_to_lead  # 0.1 is the top rate and is extended (0.3, then 1.0): once 1.0 is measured at 0 the best is 0.1 again, no longer at the end
    no_up = K.run_calibration(TableEngine({2048: 99999, 8192: 8192, 32768: 16384}, LADDER_OK))
    assert any("row 2048: no U_P" in r for r in no_up.returns_to_lead) and not no_up.ladder and not K.to_record(no_up)["complete"]
    lad = dict(LADDER_OK)
    lad[("8K/1K", "F-OQ")] = (4.2, 30000)  # above 4.0 bits: F-OQ not full at its U0 -> returns to the lead before the freeze
    nf = K.run_calibration(TableEngine({2048: 8192, 8192: 8192, 32768: 16384}, lad))
    assert any("8K/1K: F-OQ not full" in r for r in nf.returns_to_lead) and nf.ladder["8K/1K"]["returns_to_lead"]
    lad2 = {**LADDER_OK, ("2K/256", "F-OQ"): (3.0, 5_000_000)}  # 2K/256 never full: not run, no return
    sat = K.run_calibration(TableEngine({2048: 8192, 8192: 8192, 32768: 16384}, lad2))
    rec = K.to_record(sat)
    assert not sat.returns_to_lead and rec["sat256"] is False and "2K/256" not in rec["u0"] and sat.ladder["2K/256"]["note"] == "256 NOT MEASURED — NOT FULL WITHIN CEILING"
    toq = K.run_calibration(TableEngine({2048: 8192, 8192: 8192, 32768: 16384}, {**LADDER_OK, ("8K/1K", "T-OQ"): (3.0, 5_000_000)}))
    assert toq.ladder["8K/1K"]["toq_predicted_not_full"] and toq.ladder["8K/1K"]["u0"] == toq.ladder["8K/1K"]["foq_length"]
