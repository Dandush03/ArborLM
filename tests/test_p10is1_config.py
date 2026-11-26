# ruff: noqa: E501
"""P10IS1 config and core (ADR-0024): every threshold equals the specification's value, the grid, units, ladder, snapshots, DEP-c quantile (against exact integer arithmetic), keys and planned cells."""

import math
import sys
from fractions import Fraction
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from studies.p10is1 import core  # noqa: E402

CFG = core.load_config()

ADR_THRESHOLDS = {  # section 15 'Scientific threshold' and the tables of sections 7-9 (values written here from the ADR text, not from the config)
    "ref_r2_min": 0.95, "dep_use_floor": 0.25, "dep_c_tail": 1e-4, "dep_c_floor": 0.01, "gain_min": 0.5, "null_max": 0.25, "plateau_max": 0.10, "plateau_floor_a_use": 0.25, "plateau_floor_i_printed": 0.473,
    "loaded_i_max": 4.0, "ceiling_i": 4.5, "a_use_floor_capacity": 0.5, "arm_a_use_at_largest": 0.80, "dense_ahead_bits": -0.25, "beats_dense_ratio": 1.10, "tree_ahead_ratio": 1.03, "tree_competitive_ratio": 0.97,
    "saturation_ratio": 3.0, "efficiency_i_t": 3.0, "efficiency_updates_factor": 0.5, "efficiency_cost_factor": 0.8, "dense_faster_cost": 0.8, "calibration_a_use_foq": 0.90, "calibration_a_use_r2": 0.95,
    "undertrained_a_use": 0.90, "paired_all": 5, "paired_most": 4, "replicates": 5,
}  # fmt: skip


def test_every_threshold_equals_the_adr_value() -> None:
    for k, v in ADR_THRESHOLDS.items():
        assert CFG["thresholds"][k] == v, k
    assert round(core.floor_i_bits(0.25), 3) == CFG["thresholds"]["plateau_floor_i_printed"] == 0.473
    assert CFG["mc"]["grid"] == [1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 6.0]
    assert CFG["rates"]["grid"] == [0.001, 0.003, 0.01, 0.03, 0.1] and CFG["rates"]["tie_difference"] == 0.02
    assert CFG["rates"]["extension_up"][0] == 0.3 and CFG["rates"]["extension_down"][0] == 0.0003 and CFG["rates"]["extensions_max"] == 2
    assert CFG["rates"]["provisional_readout"] == {"2048": 8192, "8192": 8192, "32768": 16384} and CFG["rates"]["loaded_readout"] == 65536
    assert CFG["ladder"]["u_p_candidates"] == [8192, 16384, 32768, 65536] and CFG["ladder"]["u_p_ceiling"] == 65536 and CFG["ladder"]["levels"] == 4 and CFG["ladder"]["run_multiplier"] == 6
    assert CFG["ladder"]["snapshot_fractions"] == [1 / 16, 1 / 8, 1 / 4, 1 / 2, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 6.0]
    assert CFG["ladder"]["calibration_ceiling"] == {"8192/1024": 1572864, "2048/256": 1572864, "32768/4096": 3145728}  # 4 x P10-S1's run lengths
    assert {k: 4 * v for k, v in CFG["ladder"]["p10s1_run"].items()} == CFG["ladder"]["calibration_ceiling"]
    assert CFG["ladder"]["calibration_i_max"] == 4.0
    assert CFG["budget"]["total_cap_hours"] == 60.0 and CFG["budget"]["level_count"] == 4
    q = CFG["quiet"]
    assert "load_average_max" not in q  # ADR-0024 addendum A8 item 2: removed, not left at 1.0
    assert q["poll_seconds"] == 600 and q["session_hours"] == 6 and q["attempts"] == 6 and q["not_measured_after_paused_attempts"] == 6
    assert (q["load_margin"], q["load_ceiling"], q["load_report_above"], q["percentile"], q["baseline_samples"], q["baseline_interval_seconds"], q["settle_samples"]) == (50, 300, 250, 95, 360, 10, 60)
    assert (q["settled_median_diff_max"], q["settled_p95_diff_max"], q["sample_gap_max_seconds"], q["hid_idle_min_seconds"], q["end_load_delay_seconds"]) == (25, 50, 15, 600, 120)
    assert (q["timing_spread_max"], q["timing_spread_sessions_to_human_lead"], q["open_sessions_before_closed"], q["closed_sessions_to_human_lead"], q["baseline_session_hours"], q["baseline_attempt_minutes"]) == (0.05, 3, 3, 3, 6, 70)
    assert len(q["vm_markers"]) == 16 and q["app_markers"] == ["/Applications/Claude\\.app/Contents/MacOS/Claude"] and len(q["cli_markers"]) == 1
    assert q["condition"] in ("open", "closed") and isinstance(q["baseline_provisional"], bool) and isinstance(q["app_present"], bool) and isinstance(q["cli_present"], bool)
    m = CFG["memory_check"]
    assert m["retry_seconds"] == 600 and m["max_hours"] == 6 and m["page_kinds"] == ["free", "inactive", "purgeable", "speculative"]
    p = CFG["platform"]
    assert (p["system"], p["machine"], p["torch"], p["torch_num_threads"], p["torch_interop_threads"], p["deterministic_algorithms"]) == ("Darwin", "arm64", "2.8.0", 1, 1, True)
    assert CFG["resources"]["rss_worker_bytes"] == 3 * 1024**3 and CFG["resources"]["rss_aggregate_bytes"] == 18 * 1024**3 and CFG["resources"]["workers"] == 6
    assert CFG["seed_ranges"]["checker_sha256"] == "e462360420321aa284b0e4d47b106806419ab616794a5c632fee70f122c67594"


def test_seed_values_equal_the_registry() -> None:
    s = CFG["seeds"]
    assert [core.registered_base(d) for d in range(1, 6)] == [240001, 240101, 240201, 240301, 240401]
    assert [core.init_seed_of(d) for d in range(1, 6)] == [330101, 330102, 330103, 330104, 330105]
    assert s["calibration_bases"] == [249001, 249101] and s["calibration_init"] == [330191, 330193] and s["rehearsal_base"] == 249201 and s["rehearsal_init"] == 330192
    assert s["test_init"] == [330198, 330199] and (s["test_base"], s["test_top"]) == (933001, 933999) and s["h8_offset"] == 40 and s["index_offset"] == 60
    assert core.seed_set_values(core.registered_seeds(1)).issuperset({240001 + 40, 240001 + 60})
    for k in range(9):
        vals = core.seed_set_values(core.test_seeds(k))
        assert all(933001 <= v <= 933999 for v in vals)
    with pytest.raises(ValueError):
        core.test_seeds(9)
    with pytest.raises(ValueError):
        core.registered_base(6)
    rng = CFG["seed_ranges"]
    for d in range(1, 6):
        assert all(rng["registered"][0] <= v <= rng["registered"][1] for v in core.seed_set_values(core.registered_seeds(d)))
    for k in (1, 2):
        assert all(rng["calibration"][0] <= v <= rng["calibration"][1] for v in core.seed_set_values(core.calibration_seeds(k)))
    assert all(rng["rehearsal"][0] <= v <= rng["rehearsal"][1] for v in core.seed_set_values(core.rehearsal_seeds()))


def test_grid_arms_units() -> None:
    assert core.trained_configurations() == 31 and core.trained_configurations(sat256=False) == 30
    assert {a: len(core.arm_cells(a)) for a in core.ARMS} == {"F-OQ": 8, "T-OQ": 7, "H8": 7, "D-OQ": 6, "R2": 3}
    assert core.arm_cells("D-OQ") == ((2048, 4096), (8192, 4096), (8192, 16384), (32768, 16384), (8192, 1024), (32768, 4096))
    assert core.ladder_cells() == ((2048, 256), (8192, 1024), (32768, 4096)) and core.ladder_cells(sat256=False) == ((8192, 1024), (32768, 4096))
    assert [s.name for s in core.steps()] == ["C1", "N1", "C2", "N2"] and core.transitions() == {"1K→4K": ["C1", "N1"], "4K→16K": ["C2", "N2"]}
    assert core.unit_key("F-OQ", 2048, 1024) == "F-OQ|1024" and core.unit_key("T-OQ", 8192, 1024) == "T-OQ|8K/1K" and core.unit_key("H8", 32768, 4096) == "H8|32K/4K" and core.unit_key("F-OQ", 2048, 256) == "F-OQ|2K/256"
    assert core.unit_key("D-OQ", 2048, 4096) == core.unit_key("D-OQ", 8192, 4096) == "D-OQ|4096" and core.unit_key("D-OQ", 8192, 16384) == "D-OQ|16384" and core.unit_key("R2", 32768, 32768) == "R2|32K/32K"
    assert core.unit_selection_cell("F-OQ|1024") == (2048, 1024) and core.unit_selection_cell("T-OQ|4096") == (8192, 4096) and core.unit_selection_cell("H8|16384") == (32768, 16384)
    assert core.unit_selection_cell("D-OQ|8K/1K") == (8192, 1024) and core.unit_selection_cell("R2|8K/16K") == (8192, 16384) and core.unit_selection_cell("F-OQ|2K/256") == (2048, 256)
    us = core.units()
    assert len(us) == 23 and sum(1 for u in us if core.unit_is_loaded(u)) == 9 and not any(u.startswith("D-OQ|1024") for u in us)
    assert core.saturation_pairs()["F-OQ"] == ((256, 1024), (1024, 4096)) and core.saturation_cell_of_slots(256) == (2048, 256)


def test_ladder_levels_and_snapshots() -> None:
    assert core.ladder_points(1572864) == [65536, 98304, 131072, 196608, 262144, 393216, 524288, 786432, 1048576, 1572864]
    assert core.levels_above(393216) == [524288, 786432, 1048576, 1572864]  # 1.333, 2, 2.667, 4 x U0 for a U0 of P10-S1's form
    assert core.levels_above(786432) == [1048576, 1572864, 2097152, 3145728]
    assert core.levels_above(131072) == [196608, 262144, 393216, 524288]  # 1.5, 2, 3, 4 x U0 for a power of two
    assert core.levels_above(98304)[-1] == 4 * 98304
    with pytest.raises(ValueError):
        core.levels_above(100000)
    assert core.doubling_snapshots() == [512, 1024, 2048, 4096, 8192, 16384]
    snaps = core.loaded_snapshots(8192, 786432)
    for must in (512, 16384, 32768, 49152, 65536, 98304, 393216, 786432, 8192, 10240, 12288, 16384, 20480, 24576, 32768, 49152):
        assert must in snaps
    assert max(snaps) == 786432 and snaps == sorted(set(snaps))
    assert core.grid_snapshots(8192, 49152) == [512, 1024, 2048, 4096, 8192, 10240, 12288, 16384, 20480, 24576, 32768, 49152]
    assert core.grid_snapshots(8192, 8192) == [512, 1024, 2048, 4096, 8192]  # R2 runs U_P


def test_full_at_and_istar() -> None:
    th = core.Thresholds.from_config()
    flat = {32768: 2.0, 49152: 2.0, 65536: 2.05, 98304: 2.05}
    assert core.full_at({"A": flat, "B": flat}, 98304, 65536, plateau_max=th.plateau_max, floor_i=th.plateau_floor_i)
    rising = {32768: 1.0, 49152: 1.2, 65536: 1.5, 98304: 1.75}
    assert not core.full_at({"A": flat, "B": rising}, 98304, 65536, plateau_max=th.plateau_max, floor_i=th.plateau_floor_i)
    assert core.full_at({"A": {32768: 4.2, 49152: 4.2, 65536: 4.2, 98304: 4.2}}, 98304, 65536, plateau_max=th.plateau_max, floor_i=th.plateau_floor_i, i_max=None)
    assert not core.full_at({"A": {32768: 4.2, 49152: 4.2, 65536: 4.2, 98304: 4.2}}, 98304, 65536, plateau_max=0.1, floor_i=0.4, i_max=4.0)  # the calibration's extra condition
    assert not core.full_at({"A": {65536: 2.0, 98304: 2.0}}, 98304, 65536, plateau_max=0.1, floor_i=0.4)  # a snapshot missing
    assert core.i_star({1: 0.3, 2: 0.9, 3: 0.5}, 3) == 0.9 and core.i_star({1: 0.3, 2: 0.9, 3: 0.5}, 1) == 0.3


def _exact_quantile(m: int, num: int, den: int, tail_inv: int) -> int:
    """The smallest k with P(X <= k) >= 1 - 1/tail_inv for X ~ Binomial(m, num/den), in exact integers."""
    total = 0
    for k in range(m + 1):
        total += math.comb(m, k) * num**k * (den - num) ** (m - k)
        if total * tail_inv >= (tail_inv - 1) * den**m:
            return k
    return m


@pytest.mark.parametrize(("m", "num", "den"), [(0, 1, 32), (1, 1, 20), (50, 1, 25), (200, 1, 25), (500, 7, 160), (1200, 100, 2048), (2048, 100, 2048), (1000, 1, 3)])
def test_binomial_quantile_is_exact(m: int, num: int, den: int) -> None:
    got = core.binomial_upper_quantile(m, num / den, 1e-4)
    want = _exact_quantile(m, num, den, 10**4)
    assert abs(got - want) <= 0  # the float log-space walk reaches the same integer k except at the knife edge of the 1 - 1e-4 boundary
    assert core.binomial_upper_quantile(m, 0.0, 1e-4) == 0
    assert core.binomial_upper_quantile(m, 1.0, 1e-4) == m


def test_dep_c_requires_both_parts_and_uses_strict_exceedance() -> None:
    n = 2048
    hi = core.chance_high(n)
    u = 600
    m = n - u
    q = core.dep_c_quantile(n, u, 1e-4)
    assert q == _exact_quantile(m, hi, n, 10**4)
    b = int(0.03 * n)
    # (i) holds, (ii) fails: excess above the quantile but below the 1% effect floor
    base = q + 1
    assert core.dep_c_fails(n, u + base, u, 0, tail=1e-4, floor=0.01) == ((base - 0) / n > 0.01)
    c_small_excess = u + q  # not above the quantile: strictly greater is required
    assert not core.dep_c_fails(n, c_small_excess, u, 0, tail=1e-4, floor=0.01)
    # both hold
    big = u + int(0.10 * n)
    assert core.dep_c_fails(n, big, u, b, tail=1e-4, floor=0.01)
    # (i) holds but the excess is explained by the backbone's own rate: (ii) fails
    explained = u + q + 1
    assert not core.dep_c_fails(n, explained, u, int(n * (q + 1) / m) + 5, tail=1e-4, floor=0.01)
    assert not core.dep_c_fails(0, 0, 0, 0, tail=1e-4, floor=0.01)


def test_keys_carry_the_reads_name_and_never_collide() -> None:
    a, b = core.read_key("cell1", 512, "main"), core.read_key("cell1", 512, "ivf")
    assert a != b and core.parse_read_key(a) == ("cell1", 512, "main") and core.parse_read_key(b) == ("cell1", 512, "ivf")
    assert core.baseline_key(1, 2048) != core.baseline_key(1, 8192) and not core.baseline_key(1, 2048).startswith("eval|")
    for bad in (("", 1, "main"), ("c", 0, "main"), ("c", 1, "other")):
        with pytest.raises(ValueError):
            core.read_key(*bad)
    with pytest.raises(ValueError):
        core.parse_read_key("eval|c|u1|main")


def _params(u0: dict[str, int] | None = None, granted: dict[str, int] | None = None) -> core.PlanParams:
    rates = {u: 0.003 for u in core.units()}
    rates["D-OQ|4096"] = 0.03
    return core.PlanParams({2048: 8192, 8192: 8192, 32768: 16384}, rates, u0 or {"2K/256": 98304, "8K/1K": 393216, "32K/4K": 786432}, granted or {"2K/256": 196608, "8K/1K": 524288, "32K/4K": 1048576})


def test_planned_cells_counts_labels_lengths() -> None:
    cells = core.planned_cells(_params(), core.REGISTERED)
    assert len(cells) == 155 and len({c["label"] for c in cells}) == 155
    assert len(core.planned_cells(core.PlanParams({2048: 8192, 8192: 8192, 32768: 16384}, {u: 0.003 for u in core.units()}, {"8K/1K": 393216, "32K/4K": 786432}, {"8K/1K": 524288, "32K/4K": 1048576}, sat256=False), core.REGISTERED)) == 150
    by = {(c["arm"], c["facts"], c["slots"], c["draw"]): c for c in cells}
    assert by[("F-OQ", 2048, 1024, 1)]["run"] == 6 * 8192 and by[("R2", 8192, 16384, 1)]["run"] == 8192 and by[("F-OQ", 32768, 16384, 3)]["run"] == 6 * 16384
    assert by[("T-OQ", 8192, 1024, 2)]["run"] == 524288 and by[("T-OQ", 8192, 1024, 2)]["ladder_cell"] and by[("T-OQ", 8192, 1024, 2)]["u0"] == 393216
    assert by[("D-OQ", 2048, 4096, 1)]["lr"] == 0.03 and by[("F-OQ", 2048, 1024, 1)]["lr"] == 0.003
    assert {c["init_seed"] for c in cells if c["draw"] == 4} == {330104} and {c["seed_base"] for c in cells if c["draw"] == 4} == {240301}
    t = core.planned_cells(_params(), core.TEST, draws=[1, 2])
    assert all(933001 <= c["seed_base"] <= 933999 for c in t) and all(c["label"].startswith("TEST_") for c in t)
    r = core.planned_cells(_params(), core.REHEARSAL, draws=[1])
    assert {c["seed_base"] for c in r} == {249201} and {c["init_seed"] for c in r} == {330192}
    # every snapshot of a cell lies at or below its run length and includes it
    assert all(max(c["snapshots"]) == c["run"] and min(c["snapshots"]) >= 1 for c in cells)


def test_ledger_and_cap_rule(tmp_path) -> None:  # type: ignore[no-untyped-def]
    led = core.Ledger(tmp_path / "l.json", 100.0)
    assert led.charged() == 0 and led.remaining() == 100.0
    led.charge("train", "r1", 40.0)
    led.charge("evaluate", "r1", 70.0)
    assert led.charged() == 110.0 and led.charged("train") == 40.0 and led.remaining() == 0.0
    with pytest.raises(core.LedgerRefused):
        led.require_room("train")
    assert core.propose_cap_hours(12.0, 10.2) == 33.0 and core.propose_cap_hours(0, 0) == 0.0
    with pytest.raises(ValueError):
        core.propose_cap_hours(-1, 1)
    assert Fraction(1, 3) == Fraction(2, 6)  # keeps the Fraction import honest
