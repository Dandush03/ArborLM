# ruff: noqa: E501
"""P10IS0 ladder (ADR-0023 sections 5.1, 5.2, 9) on synthetic curves with known answers, and the config's equality with the specification's numbers."""

import sys
from fractions import Fraction as F
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from studies.p10is0 import core, labels, ladder  # noqa: E402
from studies.p10is0.ladder import Curve, Point  # noqa: E402

CFG = core.load_config()
TH = core.Thresholds.from_config(CFG)
LADDER = [512, 1024, 2048, 4096, 8192, 16384]
N = 10000


def pt(p: float, h: float | None = None) -> Point:
    return Point(F(round(p * N), N), F(round((p if h is None else h) * N), N))


def curves(a5: dict[int, float], a6: dict[int, float], hs: dict[str, dict[int, float]] | None = None) -> dict[tuple[str, int], Curve]:
    out = {}
    for arm, series in (("A5-D", a5), ("A6", a6)):
        for d in (1, 2):
            out[(arm, d)] = Curve(arm, d, {e: pt(v) for e, v in series.items()})
    return out


FLAT_HIGH = {512: 0.95, 1024: 0.95, 2048: 0.95, 4096: 0.95, 8192: 0.95, 16384: 0.95}


def test_config_equals_the_specification() -> None:
    t = CFG["thresholds"]
    assert (t["success_fraction_of_a6"], t["heldout_fraction"], t["dependence_fraction"], t["a6_floor_anchor"], t["a6_floor_loaded"], t["stable_threshold"]) == (0.90, 0.90, 0.95, 0.90, 0.50, 0.80)
    assert (t["max_failed_reliable"], t["max_not_evaluated_draws"], t["min_successes"], t["line_fail_cells"]) == (1, 1, 3, 2)
    assert (t["plateau_step"], t["plateau_steps_required"], t["confirm_step"], t["t_factor"], t["paired_d"], t["paired_p"]) == (0.01, 2, 0.02, 2, 6, 0.05)
    assert CFG["ladder"]["base"] == LADDER and CFG["ladder"]["extension_ceiling"] == 32768 and CFG["ladder"]["base_ceiling_t"] == 8192 and CFG["ladder"]["extended_ceiling_t"] == 16384
    assert CFG["budget"]["b_hours"] == 55.0 and CFG["budget"]["workers"] == 6
    d = CFG["draws"]
    assert (d["registered"], d["reserve"], d["calibration"], d["checkpoint_probe_every"], d["checkpoint_probe_every_late"], d["checkpoint_probe_switch"]) == (10, 4, 2, 64, 1024, 4096)
    r = CFG["resources"]
    assert (r["rss_worker_bytes"], r["rss_aggregate_bytes"], r["combined_aggregate_bytes"], r["memory_growth_mib"], r["disk_cap_bytes"], r["disk_free_min_bytes"]) == (3 * 2**30, 18 * 2**30, 36 * 2**30, 64, 110 * 2**30, 50 * 2**30)
    assert r["memory_budget_bytes"] == 9 * 2**30
    tm = CFG["timing"]
    assert (tm["quiet_load_max"], tm["attempts"], tm["attempt_window_hours"], tm["min_updates"], tm["busy_processes"], tm["sample_seconds"], tm["sample_window_seconds"], tm["workers"]) == (2.0, 3, 24, 8192, 12, 10, 60, 6)
    i = CFG["identity"]
    assert i["tolerance"] == 1e-6 and i["long_updates"] == 5184 and i["p10s0_cadence"] == 64 and i["end_to_end_slots"] == [512, 1024, 2048, 8192]
    assert i["fact_counts_a5d_a6"] == [[2048, 4096], [8192, 16384], [8192, 4096]] and i["fact_counts_a0"] == [[8192, 4096], [8192, 16384]]
    s = CFG["seeds"]
    assert (s["registered_base"], s["draw_stride"], s["reserve_bases"], s["calibration_bases"], s["rehearsal_base"], s["check_base"]) == (300001, 100, [301001, 301101, 301201, 301301], [309001, 309101], 309201, 309301)
    assert (s["init_registered"], s["init_calibration"], s["init_rehearsal"], s["test_init"], s["test_base"], s["test_top"]) == ([330001, 330002], [330091, 330093], 330092, [330098, 330099], 932001, 932999)
    assert (s["repeat_cal_first"], s["repeat_cal_second"], s["repeat_init_first"], s["repeat_init_second"]) == (309401, 309501, 330061, 330062)
    assert (s["identity_gate_data_base"], s["identity_gate_init"]) == (209101, 2092)
    assert CFG["seed_ranges"]["checker_sha256"] == "e462360420321aa284b0e4d47b106806419ab616794a5c632fee70f122c67594"
    grid = [(c["series"], c["facts"], c["slots"], tuple(c["arms"])) for c in CFG["grid"]["cell_types"]]
    assert grid[:4] == [("M", 8192, s_, ("A5-D", "A0", "A6")) for s_ in (16384, 8192, 4096, 2048)]
    assert grid[4:8] == [("S", 2048, s_, ("A5-D", "A6")) for s_ in (4096, 2048, 1024, 512)] and grid[8] == ("X", 8192, 1024, ("A5-D", "A0", "A6"))
    assert [ct.load for ct in core.cell_types(CFG)] == [0.5, 1, 2, 4, 0.5, 1, 2, 4]
    assert len(core.registered_cells(CFG)) == 200 and len(core.registered_cells(CFG, include_x8=True)) == 230


def test_exposures_and_updates() -> None:
    assert core.updates_for(512, 2048) == 8192 and core.updates_for(512, 8192) == 32768
    assert core.updates_for(8192, 8192) == 524288 and core.updates_for(8192, 2048) == 131072


def test_plateau_at_the_first_ladder_value() -> None:
    d = ladder.decide_cell_type(curves(FLAT_HIGH, FLAT_HIGH), 0.9, 16384, TH, LADDER, cfg=CFG)
    assert (d.status, d.e_star, d.t, d.shown, d.flat_below_floor) == (ladder.STATUS_SHOWN, 512, 1024, True, False)


def test_undecided_until_the_points_exist_then_a_later_plateau() -> None:
    rising = {512: 0.5, 1024: 0.7, 2048: 0.85, 4096: 0.90, 8192: 0.91, 16384: 0.915}
    assert ladder.decide_cell_type(curves({k: v for k, v in rising.items() if k <= 2048}, {k: v for k, v in rising.items() if k <= 2048}), 0.5, 16384, TH, LADDER, cfg=CFG).status == ladder.STATUS_UNDECIDED
    d = ladder.decide_cell_type(curves(rising, rising), 0.5, 16384, TH, LADDER, cfg=CFG)
    assert (d.status, d.e_star, d.t) == (ladder.STATUS_SHOWN, 4096, 8192)  # 0.90 -> 0.91 -> 0.915 are steps of 0.01 and 0.005


def test_two_sided_a_fall_is_not_a_plateau() -> None:
    falling = {512: 0.95, 1024: 0.95, 2048: 0.90, 4096: 0.85, 8192: 0.80, 16384: 0.75}
    held = ladder.decide_cell_type(curves(falling, FLAT_HIGH), 0.9, 16384, TH, LADDER, cfg=CFG)
    assert held.status == ladder.STATUS_CANDIDATE


def test_floor_on_the_reference_only() -> None:
    low = dict.fromkeys(LADDER, 0.30)
    d = ladder.decide_cell_type(curves(FLAT_HIGH, low), 0.5, 16384, TH, LADDER, cfg=CFG)
    assert d.status == ladder.STATUS_CANDIDATE  # the reference never reached the floor: no plateau counts
    d = ladder.decide_cell_type(curves(low, FLAT_HIGH), 0.5, 16384, TH, LADDER, cfg=CFG)
    assert d.status == ladder.STATUS_SHOWN and d.flat_below_floor and d.label == labels.FLAT_BELOW_FLOOR and d.e_star == 512


def test_ceilings_extension_and_non_finite() -> None:
    wobble = {512: 0.5, 1024: 0.6, 2048: 0.7, 4096: 0.8, 8192: 0.9, 16384: 0.95}
    assert ladder.decide_cell_type(curves(wobble, wobble), 0.5, 16384, TH, LADDER, cfg=CFG).status == ladder.STATUS_CANDIDATE
    ext = {**wobble, 32768: 0.96}
    d = ladder.decide_cell_type(curves(ext, ext), 0.5, 32768, TH, LADDER, cfg=CFG)
    assert d.status == ladder.STATUS_CEILING and d.t == 16384 and d.label == labels.NOT_SHOWN_REHEARSAL
    flat_late = {**wobble, 16384: 0.905, 32768: 0.91}  # 0.8 -> 0.9 is not flat at 4096; at 8192: 0.9, 0.905, 0.91 is
    d = ladder.decide_cell_type(curves(flat_late, flat_late), 0.5, 32768, TH, LADDER, cfg=CFG)
    assert (d.status, d.e_star, d.t) == (ladder.STATUS_SHOWN, 8192, 16384)
    cv = curves(FLAT_HIGH, FLAT_HIGH)
    cv[("A6", 2)].nonfinite_update = 77
    nf = ladder.decide_cell_type(cv, 0.9, 16384, TH, LADDER, cfg=CFG)
    assert nf.status == ladder.STATUS_NONFINITE and nf.t == 8192 and nf.label == labels.NON_FINITE_REHEARSAL != labels.NOT_SHOWN_REHEARSAL


def test_the_largest_t_on_the_base_ladder_is_8192() -> None:
    assert max(e for e in ladder.candidate_es(16384, LADDER, TH)) * 2 == 8192
    assert max(ladder.candidate_es(32768, LADDER, TH)) * 2 == 16384


def rates(per_update: float = 0.01, ev: float = 100.0) -> ladder.Rates:
    keys = [(a, ct.slots) for ct in core.cell_types(CFG, include_x8=True) for a in ct.arms]
    return ladder.Rates({k: per_update for k in keys}, {k: ev for k in keys})


def test_extension_rule_order_budget_and_continue_after_refusal() -> None:
    cts = core.cell_types(CFG)
    x8 = core.cell_type_by_name("8K/1K", CFG)
    t_known = {ct.name: 2048 for ct in cts}
    cands = [core.cell_type_by_name(n, CFG) for n in ("2K/512", "8K/4K", "2K/4K")]  # deliberately out of order
    dec = ladder.decide_extensions(cands, cts=cts, t_known=t_known, rates=rates(0.002), charged_hours=0.0, other_hours=1.5, x8=x8, cfg=CFG)
    assert [d.cell_type for d in dec] == ["2K/4K", "8K/4K", "2K/512"]  # ascending load; the 0.5 load first
    assert all(d.budget_hours == 55.0 for d in dec)
    assert [d.granted for d in dec][0] is True
    # a tight budget: refuse the big one, still try the next
    tight = {**{k: v for k, v in CFG.items()}, "budget": {**CFG["budget"], "b_hours": 1e-9}}
    assert not any(d.granted for d in ladder.decide_extensions(cands, cts=cts, t_known=t_known, rates=rates(0.002), charged_hours=0.0, other_hours=0.0, x8=x8, cfg=tight))
    # continue after refusal: budget between the cheap and the expensive cell type
    lo = ladder.decide_extensions(cands[:1], cts=cts, t_known=t_known, rates=rates(0.002), charged_hours=0.0, other_hours=0.0, x8=x8, cfg=CFG)[0].projected_hours
    mid = {**CFG, "budget": {**CFG["budget"], "b_hours": lo + 0.0001}}
    out = ladder.decide_extensions([core.cell_type_by_name("8K/4K", CFG), core.cell_type_by_name("2K/512", CFG)], cts=cts, t_known=t_known, rates=rates(0.002), charged_hours=0.0, other_hours=0.0, x8=x8, cfg=mid)
    assert out[0].granted is False and out[0].projected_hours > lo  # the expensive one is refused; the next candidate is still tried
    assert out[1].cell_type == "2K/512" and out[1].projected_hours > 0


def test_projection_arithmetic() -> None:
    ct = core.cell_type_by_name("2K/4K", CFG)
    r = rates(0.01, 0.0)
    p, stages = ladder.projected_hours(cts=[ct], t_assumed={ct.name: 512}, granted_rounds=[], rates=r, charged_hours=1.0, other_hours=0.5, x8=None, workers=6, ladder_top=16384, x8_t=0)
    per_cell = 0.01 * 8192
    assert stages[0].total_seconds == pytest.approx(per_cell * 20) and stages[0].longest_seconds == pytest.approx(per_cell * 2)  # one task per (cell type, draw): its two arms
    assert p == pytest.approx(1.5 + (per_cell * 20 / 6 + per_cell * 2) / 3600)


def test_worker_count_rule() -> None:
    gib = 2**30
    assert ladder.worker_count(int(0.5 * gib), CFG) == 6
    assert ladder.worker_count(int(1.5 * gib), CFG) == 6
    assert ladder.worker_count(2 * gib, CFG) == 4
    assert ladder.worker_count(3 * gib, CFG) == 3
    with pytest.raises(ladder.EngineeringStop, match="3 GiB"):
        ladder.worker_count(3 * gib + 1, CFG)  # R6: above the per-worker guard it is PAUSED before it starts


def obs(acc: float = 0.95, **kw: object) -> labels.Obs:
    n = 1000
    c = round(acc * n)
    base = {"a": (c, n), "b": (c, n), "h1": (c, n), "h2": (c, n), "dep_chance_a": True, "dep_chance_b": True, "leakage": False, "distinct_top1": 200, "largest_share": 0.01, "probe_facts": 256, "lm_rise": 0.0, "a_use_a": acc, "a_use_b": acc}
    base.update(kw)
    return labels.Obs(**base)  # type: ignore[arg-type]


def test_reference_flags() -> None:
    f, info = ladder.reference_flags({1: obs(), 2: obs()}, 0.9, TH)
    assert f == labels.RefFlags() and info["computed_on_draws"] == [1, 2]
    f, _ = ladder.reference_flags({1: obs(h1=(500, 1000)), 2: obs()}, 0.9, TH)
    assert f == labels.RefFlags(cond4=True)
    f, _ = ladder.reference_flags({1: obs(), 2: obs(leakage=True, a_use_a=0.1)}, 0.9, TH)
    assert f == labels.RefFlags(other=(5, 6))
    f, info = ladder.reference_flags({1: obs(0.4, h1=(1, 1000)), 2: obs()}, 0.9, TH)
    assert info["reference_below_floor_at_t_draws"] == [1] and f == labels.RefFlags()  # no flag computed on a draw below the floor
    f, info = ladder.reference_flags({1: None, 2: obs(distinct_top1=3)}, 0.9, TH)
    assert f.other == (3,) and info["computed_on_draws"] == [2]


def test_events_by_rule_and_durations_whitelist() -> None:
    cts = core.cell_types(CFG)
    ok = {"convergence": "SHOWN", "reference_flags": {"cond4": False, "other": []}}
    ent = {ct.name: dict(ok) for ct in cts}
    assert ladder.events(ent, cts) == []
    ent["8K/16K"] = {"convergence": labels.NOT_SHOWN_REFUSED, "flat_below_floor": True, "reference_flags": {"cond4": True, "other": []}}
    ent["8K/8K"] = {**ok, "reference_flags": {"cond4": True, "other": []}}
    ent["8K/2K"] = {**ok, "reference_flags": {"cond4": False, "other": [2]}}  # load 4: not an event
    ent["2K/1K"] = {**ok, "reference_below_floor_at_t": [1]}
    ev = ladder.events(ent, cts)
    assert len(ev) == 3 and ev[0].startswith("(a) anchor 8K/16K") and "(b)" in ev[1] and "(c) 2K/1K" in ev[2]
    with pytest.raises(ValueError):
        ladder.durations_record({"8K/4K": {"e_star": 512, "m_p": 0.9}})
    assert ladder.durations_record({"8K/4K": {"e_star": 512, "t_exposures": 1024}})["cell_types"]["8K/4K"]["t_exposures"] == 1024


def test_stage_r_cap_formula() -> None:
    cts = core.cell_types(CFG)
    r = rates(0.01, 0.0)
    base = ladder.stage_r_cap_hours(cts, r, [], CFG)
    expected = 2 * sum(0.01 * ct.updates(16384) * 4 for ct in cts) / 6 / 3600
    assert base == pytest.approx(expected)
    assert ladder.stage_r_cap_hours(cts, r, ["8K/4K"], CFG) > base
