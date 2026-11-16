# ruff: noqa: E501
"""P10S1 revision 5: the plateau floor on revision 4's curves, the load search, U_L of each cell, U_P of each row, D-OQ's rate per unit, and the calibration rules applied to a finished record on
synthetic counts (ADR-0021 sections 8.2 and 10.1; brief groups 2 to 5). Nothing is trained; no seed is read. Self-check only: not independent review, not Astra validation, not human approval."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from studies.p10s1 import calibrate, core  # noqa: E402
from studies.p10s1 import classes as C  # noqa: E402
from studies.p10s1 import synthetic as syn  # noqa: E402

REVISION_4_CURVES = {  # F-OQ, calibration draw 1, Panel A: i (bits per fact) by update, rounded to 4 places; copied as numbers from docs/reviews/p10s1-load-search-2026-11-15/audit_curves.json
    "4096|8192|1|A": {512: 0.0028, 1024: 0.0257, 2048: 0.5326, 4096: 2.9886, 8192: 4.5395, 16384: 4.8527, 24576: 4.9131, 32768: 4.9221, 49152: 4.9566, 65536: 4.9599},
    "4096|16384|1|A": {512: 0.0, 1024: 0.0019, 2048: 0.05, 4096: 0.5307, 8192: 2.1362, 16384: 3.2744, 24576: 3.6738, 32768: 3.8557, 49152: 4.0318, 65536: 4.1104},
    "4096|32768|1|A": {512: 0.0, 1024: 0.0, 2048: 0.0, 4096: 0.0513, 8192: 0.4136, 16384: 1.1356, 24576: 1.4559, 32768: 1.6495, 49152: 1.8642, 65536: 1.9433},
    "4096|65536|1|A": {512: 0.0, 1024: 0.0, 2048: 0.0, 4096: 0.0, 8192: 0.0565, 16384: 0.2486, 24576: 0.4297, 32768: 0.5475, 49152: 0.6814, 65536: 0.7512},
    "16384|8192|1|A": {512: 0.0104, 1024: 0.0552, 2048: 1.9794, 4096: 4.8348, 8192: 4.9955, 16384: 4.9976, 32768: 5.0, 65536: 5.0},
    "16384|32768|1|A": {512: 0.0, 1024: 0.0, 2048: 0.0178, 4096: 0.3789, 8192: 2.6069, 16384: 4.2281, 32768: 4.7188, 65536: 4.8643},
    "16384|65536|1|A": {512: 0.0, 1024: 0.0, 2048: 0.0, 4096: 0.0165, 8192: 0.3634, 16384: 1.7047, 32768: 2.8931, 65536: 3.5401},
    "16384|131072|1|A": {512: 0.0, 1024: 0.0, 2048: 0.0, 4096: 0.0, 8192: 0.0228, 16384: 0.2779, 32768: 0.9702, 65536: 1.5084},
}

N = 32768


def obs_of(i: float, n: int = N) -> C.PanelObs:
    a = core.i_to_a_use(i) if i > 0 else 1 / 32
    useful = int(round(a * n))
    return C.PanelObs(n, useful, useful, n // 32, n // 32, None, 2048, 64)


def view_of(curve: dict[int, float], run: int, u_p: int = 8192) -> C.View:
    return C.View({u: obs_of(i) for u, i in curve.items()}, run, u_p)


def four(curve: dict[int, float], run: int = 262144) -> dict[tuple[int, str], C.View]:
    return {(d, p): view_of(curve, run) for d in (1, 2) for p in "AB"}


CANDIDATES = (65536, 98304, 131072, 196608, 262144)
HALVES = (32768, 49152, 65536, 98304, 131072)


# --- group 2: the plateau floor -----------------------------------------------------------------------------------------------------------------------
def test_on_revision_4s_curves_no_cell_is_loaded_at_1024_to_8192_updates_and_a_flat_cell_below_the_floor_is_labelled() -> None:
    old_rule_said_loaded = []
    for key, curve in REVISION_4_CURVES.items():
        for u in (1024, 2048, 4096, 8192):
            v = view_of({k: x for k, x in curve.items() if k <= u}, u)
            assert not v.plateaued() and not v.loaded(), (key, u)  # revision 5: nobody is loaded before it has learned
            if v.gain_flat() and C.le(v.i_star(u)[0], core.LOADED_I_MAX):
                old_rule_said_loaded.append((key, u))
                assert v.plateau_status() == C.FLAT_BELOW_FLOOR and not v.above_floor()  # the gain condition alone is met: printed FLAT BELOW THE DEP FLOOR, not "still improving"
            else:
                assert v.plateau_status() in (C.RISING, C.FLAT_BELOW_FLOOR)
    assert old_rule_said_loaded  # revision 4's letter of section 8.2 called these cells loaded
    assert core.PLATEAU_FLOOR_I == pytest.approx(0.473, abs=5e-4)


def test_flat_below_the_floor_is_printed_on_a_step_verdict_and_a_genuine_plateau_is_not_confused_with_it() -> None:
    flat_low = view_of({512: 0.02, 1024: 0.03, 2048: 0.03, 4096: 0.03, 8192: 0.03, 16384: 0.04}, 8192 * 2)
    assert flat_low.gain_flat() and not flat_low.above_floor() and flat_low.plateau_status() == C.FLAT_BELOW_FLOOR
    plateau = view_of({512: 0.1, 1024: 0.6, 2048: 1.5, 4096: 2.0, 8192: 2.0, 16384: 2.02}, 16384)
    assert plateau.plateau_status() == C.PLATEAUED and plateau.plateaued()
    rising = view_of({512: 0.1, 1024: 0.6, 2048: 1.5, 4096: 2.0, 8192: 2.5, 16384: 3.0}, 16384)
    assert rising.plateau_status() == C.RISING
    large = view_of({512: 0.5, 1024: 2.0, 2048: 4.0, 4096: 4.8, 8192: 4.9, 16384: 4.95}, 16384)
    res = C.capacity_panel(flat_low, large, C.McEntry("OK", 8192, 8192, 1.0, "small"), ref_ok=True)
    assert res.verdict != C.NULL and res.detail["smaller_plateau_status"] == C.FLAT_BELOW_FLOOR and C.FLAT_BELOW_FLOOR in res.detail.get("note", "")


# --- group 3: the load search ---------------------------------------------------------------------------------------------------------------------
def curve(values: dict[int, float]) -> dict[int, float]:
    return {u: values[u] for u in sorted(values)}


def test_a_first_pass_alone_gives_no_u_l_two_consecutive_passes_give_the_second_and_pass_fail_pass_pass_gives_the_last() -> None:
    first_only = curve({32768: 1.0, 49152: 1.0, 65536: 1.0, 98304: 2.0, 131072: 3.0, 196608: 3.9, 262144: 4.5})
    v = four(first_only)
    assert calibrate.passes_at(v, 65536) and not calibrate.passes_at(v, 98304) and calibrate.arm_u_l(v, CANDIDATES) is None  # a first pass alone is not U_L
    flat_from_100k = curve({32768: 0.82, 49152: 1.23, 65536: 1.64, 98304: 2.46, 131072: 2.5, 196608: 2.5, 262144: 2.5})
    w = four(flat_from_100k)
    assert [calibrate.passes_at(w, u) for u in CANDIDATES] == [False, False, False, True, True] and calibrate.arm_u_l(w, CANDIDATES) == 262144  # two consecutive passes give the second
    pfpp = curve({32768: 2.0, 49152: 2.0, 65536: 2.08, 98304: 2.15, 131072: 2.17, 196608: 2.18, 262144: 2.18})
    x = four(pfpp)
    assert [calibrate.passes_at(x, u) for u in CANDIDATES] == [True, False, True, True, True] and calibrate.arm_u_l(x, CANDIDATES) == 196608  # pass-fail-pass-pass gives the last pass pair, not the first pass
    consecutive = curve({32768: 2.0, 49152: 2.0, 65536: 2.0, 98304: 2.0, 131072: 2.0, 196608: 2.0, 262144: 2.0})
    assert calibrate.arm_u_l(four(consecutive), CANDIDATES) == 98304  # the second of the first two consecutive passes


def test_a_view_above_four_bits_a_failed_run_a_capped_run_and_one_failing_view_give_no_u_l() -> None:
    high = curve({32768: 4.2, 49152: 4.2, 65536: 4.2, 98304: 4.2, 131072: 4.2, 196608: 4.2, 262144: 4.2})
    assert calibrate.arm_u_l(four(high), CANDIDATES) is None  # i* above 4.0 at every candidate
    flat = curve(dict.fromkeys(HALVES + (196608, 262144), 2.0))
    ok = four(flat)
    assert calibrate.arm_u_l(ok, CANDIDATES) == 98304
    bad = dict(ok)
    bad[(2, "B")] = view_of(high, 262144)
    assert calibrate.arm_u_l(bad, CANDIDATES) is None  # all four views must pass
    assert calibrate.arm_u_l(None, CANDIDATES) is None and calibrate.arm_u_l({}, CANDIDATES) is None  # a failed run or a run stopped at its item cap has no views
    short = {k: view_of({u: i for u, i in flat.items() if u <= 65536}, 65536) for k in ok}
    assert calibrate.arm_u_l(short, CANDIDATES) is None  # the run stopped before the later candidates
    assert calibrate.arm_u_l(four(curve({32768: 0.2, 49152: 0.2, 65536: 0.2, 98304: 0.2, 131072: 0.2, 196608: 0.2, 262144: 0.2})), CANDIDATES) is None  # flat below the floor never passes


def test_the_fixed_outcomes_of_the_load_search_and_the_256_cell() -> None:
    both = calibrate.cell_outcome(131072, 196608)
    assert both["action"] == calibrate.GRID_STANDS and both["u_l"] == 196608 and not both["toq_predicted_not_loaded"]
    only = calibrate.cell_outcome(131072, None)
    assert only["action"] == calibrate.GRID_STANDS and only["u_l"] == 131072 and only["toq_predicted_not_loaded"] and calibrate.TOQ_PREDICTED_NOT_LOADED in only["note"]
    none = calibrate.cell_outcome(None, 196608)
    assert none["action"] == calibrate.RETURN_TO_LEAD and none["u_l"] is None and none["status"] == calibrate.NOT_LOADED_WITHIN_CEILING
    assert calibrate.cell_outcome(None, None)["action"] == calibrate.RETURN_TO_LEAD
    s = calibrate.saturation_cell_outcome(98304)
    assert s["runs"] and s["u_l"] == 98304 and s["action"] == calibrate.GRID_STANDS
    n = calibrate.saturation_cell_outcome(None)
    assert not n["runs"] and n["status"] == "256 NOT MEASURED — NOT FULL WITHIN CEILING" and n["action"] == calibrate.GRID_STANDS  # no return to the human lead
    plan = core.Plan(sat256=False, u_l=(65536, 131072))
    assert len(core.registered_cells(plan, dense_rates={})) == 155 - 5 + 14 and len(core.registered_cells(core.Plan(sat256=False, seed_block_draws=()))) == 150


# --- group 4: U_P of each row ---------------------------------------------------------------------------------------------------------------------
def test_each_row_u_p_candidate_is_selected_and_none_returns() -> None:
    def table(foq: dict[int, float], r2: dict[int, float]) -> tuple[dict, dict]:
        f = {(u, d, p): a for u, a in foq.items() for d in (1, 2) for p in "AB"}
        r = {(u, d, p): a for u, a in r2.items() for d in (1, 2) for p in "AB"}
        return f, r

    cands = core.row_u_p_candidates()
    assert cands == (8192, 16384, 32768)
    for want, foq in ((8192, {8192: 0.91, 16384: 0.99, 32768: 1.0}), (16384, {8192: 0.89, 16384: 0.9, 32768: 1.0}), (32768, {8192: 0.3, 16384: 0.5, 32768: 0.97})):
        f, r = table(foq, {8192: 0.99, 16384: 1.0, 32768: 1.0})
        assert calibrate.row_u_p(f, r, cands) == {"u_p": want, "action": calibrate.GRID_STANDS}
    f, r = table({8192: 0.95, 16384: 0.95, 32768: 0.95}, {8192: 0.94, 16384: 0.94, 32768: 0.949})  # R2 never reaches 0.95
    assert calibrate.row_u_p(f, r, cands)["action"] == calibrate.RETURN_TO_LEAD and calibrate.row_u_p(f, r, cands)["u_p"] is None
    f, r = table({8192: 0.95, 16384: 0.95, 32768: 0.95}, {8192: 1.0, 16384: 1.0, 32768: 1.0})
    f[(8192, 2, "B")] = 0.899  # one view below 0.90 at the smallest candidate: the next qualifies
    assert calibrate.row_u_p(f, r, cands)["u_p"] == 16384


# --- group 5: D-OQ's rate per unit ---------------------------------------------------------------------------------------------------------------
def test_dense_rate_plain_maximum_ties_the_walk_diverged_rates_and_the_returns() -> None:
    plain = calibrate.select_dense_rate({0.001: 0.1, 0.003: 0.5, 0.01: 0.95, 0.03: 0.8, 0.1: 0.5}, None, 8192)
    assert plain["rate"] == 0.01 and plain["decided_by"] == "readout a_use" and plain["edge"] is None
    tied = {0.001: 0.1, 0.003: 0.3, 0.01: 0.95, 0.03: 0.94, 0.1: 0.5}
    traj = {0.01: {4096: 0.9, 2048: 0.5, 1024: 0.1, 512: 0.0}, 0.03: {4096: 0.6, 2048: 0.3, 1024: 0.05, 512: 0.0}}
    walked = calibrate.select_dense_rate(tied, traj, 8192)
    assert walked["rate"] == 0.01 and walked["decided_by"] == "faster learner: a_use at 4096"
    flat = {0.01: dict.fromkeys((4096, 2048, 1024, 512), 0.5), 0.03: dict.fromkeys((4096, 2048, 1024, 512), 0.51)}
    assert calibrate.select_dense_rate(tied, flat, 8192)["rate"] == 0.01 and "smaller learning rate" in calibrate.select_dense_rate(tied, flat, 8192)["decided_by"]
    with pytest.raises(calibrate.TieNeedsLead):
        calibrate.select_dense_rate(tied, None, 8192)  # the tie needs the doubling snapshots
    only_rate_walk = calibrate.select_dense_rate({0.01: 0.94, 0.1: 0.95}, {0.01: {4096: 0.5, 2048: 0.2, 1024: 0.0, 512: 0.0}, 0.1: {4096: 0.9, 2048: 0.5, 1024: 0.1, 512: 0.0}}, 8192)
    assert only_rate_walk["rate"] == 0.1 and only_rate_walk["edge"] == calibrate.EDGE_BY_TIE_WALK  # 0.1 taken only by the walk is recorded
    lead = calibrate.select_dense_rate({0.01: 0.90, 0.03: 0.9, 0.1: 0.95}, None, 8192)
    assert lead["action"] == calibrate.RETURN_TO_LEAD and lead["rate"] is None and lead["edge"] == "TOP OF GRID"  # 0.1 ahead by more than 0.02
    exact = calibrate.select_dense_rate({0.01: 0.50, 0.1: 0.52}, None, 8192)
    assert exact["action"] == calibrate.RETURN_TO_LEAD and exact["edge"] == "TOP OF GRID"  # ahead by exactly 0.02: the boundary is on the returning side (m2)
    edge_ok = calibrate.select_dense_rate({0.01: 0.5, 0.1: 0.5 + 0.015}, {0.01: dict.fromkeys((4096, 2048, 1024, 512), 0.1), 0.1: dict.fromkeys((4096, 2048, 1024, 512), 0.1)}, 8192)
    assert edge_ok["rate"] == 0.01 and edge_ok["edge"] is None  # within 0.02 and nothing separates them: the smaller rate
    div = calibrate.select_dense_rate({0.001: 0.1, 0.003: 0.5, 0.01: 0.9, 0.03: 0.0, 0.1: 0.0}, None, 8192, diverged=[0.03, 0.1])
    assert div["rate"] == 0.01 and div["diverged"] == [0.03, 0.1]
    div_top = calibrate.select_dense_rate({0.001: 0.1, 0.003: 0.5, 0.01: 0.9, 0.03: 0.0, 0.1: 0.99}, None, 8192, diverged=[0.1])
    assert div_top["rate"] == 0.01  # a diverged 0.1 is left out of the selection
    all_div = calibrate.select_dense_rate(dict.fromkeys(core.DENSE_RATES, 0.0), None, 8192, diverged=list(core.DENSE_RATES))
    assert all_div["action"] == calibrate.RETURN_TO_LEAD and all_div["rate"] is None
    assert calibrate.tie_snapshots(65536) == (32768, 16384, 8192, 4096)


# --- the rules applied to a finished record of synthetic counts --------------------------------------------------------------------------------------
def write_cell(run_dir: Path, cell: core.Cell, fn, status: str = "completed", reason: str | None = None) -> None:
    folder = core.cell_dir(run_dir, cell.label)
    core.write_record(folder / "train.json", {**core.envelope("train"), "label": cell.label, "status": status, "reason": reason, "wall_seconds": 2.0 * cell.run_updates / 1000.0, "run_updates": cell.run_updates})
    if status != "completed":
        return
    for u in calibrate.calibration_snapshots(cell):
        panels = {p: syn.panel_counts(cell.facts, core.i_to_a_use(fn(cell, u)) if fn(cell, u) > 0 else 1 / 32) for p in core.PANELS}
        core.write_record(core.eval_path(run_dir, cell.label, u), {**core.envelope("eval"), "label": cell.label, "reads": {"main": {"panels": panels, "secondary": {}}}})


def test_finalize_applies_the_rules_to_the_finished_record_and_failed_and_capped_runs_are_inputs(tmp_path: Path) -> None:
    unit = 16  # DRY unit: candidates scale by 16/8192
    cells = core.load_search_cells(unit)
    flat_at = {"8K/1K": 0.0, "32K/4K": 0.0, "2K/256": 0.0}
    cap_hit = {c.label for c in cells if c.arm == "T-OQ" and c.slots == 4096 and c.draw == 2}  # stopped at its item cap
    failed = {c.label for c in cells if c.arm == "T-OQ" and c.slots == 1024 and c.draw == 1}

    def fn(cell: core.Cell, u: int) -> float:
        cap = {1024: 2.0, 4096: 1.5, 256: 2.2}[cell.slots]
        scale = {1024: 4, 4096: 8, 256: 4}[cell.slots]  # u at which the cell is full (in units of 16 / 8192 of the registered counts)
        return cap * min(1.0, u / scale)

    run = tmp_path / "cal"
    for c in cells:
        if c.label in cap_hit:
            write_cell(run, c, fn, "failed", "ItemCapReached: stopped at update 5 of 512")
        elif c.label in failed:
            write_cell(run, c, fn, "failed", "RuntimeError: x")
        else:
            write_cell(run, c, fn)
    for c in core.row_u_p_cells(unit):
        write_cell(run, c, lambda cell, u: 4.9)
    rec = calibrate.finalize_load_and_row_up(run, unit=unit)
    assert rec["load"]["8K/1K"]["u_l"] == core.scaled(98304, unit) and rec["load"]["8K/1K"]["toq_predicted_not_loaded"] and calibrate.TOQ_PREDICTED_NOT_LOADED in rec["load"]["8K/1K"]["note"]  # T-OQ's draw-1 run failed: no U_L for T-OQ
    assert rec["load"]["32K/4K"]["u_l"] is not None and rec["load"]["32K/4K"]["arms"]["T-OQ"]["u_l"] is None and "item cap" in str(rec["load"]["32K/4K"]["arms"]["T-OQ"]["run_notes"])
    assert rec["saturation_256"]["runs"] and rec["saturation_256"]["u_l"] is not None
    assert {k: v["u_p"] for k, v in rec["row_u_p"].items()} == {"2048": 8 * 2, "8192": 8 * 2, "32768": 8 * 2} or all(v["u_p"] == 16 for v in rec["row_u_p"].values())
    assert rec["returns_to_lead"] == []
    assert calibrate.row_u_p_map(rec) == dict.fromkeys(core.ROW_FACTS, 16)
    # an F-OQ that never loads: the record returns to the human lead and items 2 and 3 cannot be mapped
    run2 = tmp_path / "cal2"
    for c in cells:
        write_cell(run2, c, lambda cell, u: 4.4)
    for c in core.row_u_p_cells(unit):
        write_cell(run2, c, lambda cell, u: 0.1)
    rec2 = calibrate.finalize_load_and_row_up(run2, unit=unit)
    assert rec2["load"]["8K/1K"]["action"] == calibrate.RETURN_TO_LEAD and rec2["returns_to_lead"] and rec2["row_u_p"]["8192"]["action"] == calibrate.RETURN_TO_LEAD and rec2["load"]["8K/1K"]["arms"]["F-OQ"]["failed_conditions"]
    assert rec2["saturation_256"]["status"] == calibrate.NOT_MEASURED_256 and not rec2["saturation_256"]["runs"]
    with pytest.raises(calibrate.TieNeedsLead):
        calibrate.row_u_p_map(rec2)
    del flat_at
