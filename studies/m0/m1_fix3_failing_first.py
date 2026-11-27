# ruff: noqa: E501
"""M1 fix round 3: apply the assertions of ``tests/test_m0_m1_fix3_*.py`` (through ``m1_fix3_checks``) to the PRE-FIX shapes (read only) and print what they find. Every line printed as
FAILS-ON-OLD is the evidence that the replacement test genuinely fails on the old code. Output is kept in the scratch directory and quoted in NOTES_FIX3_M1.md.

Run: PYTHONHASHSEED=0 uv run --locked --offline python -m studies.m0.m1_fix3_failing_first
"""

from __future__ import annotations

from studies.m0.core import lineages_of
from studies.m0.lineages_m1_common import load_batch
from studies.m0.lineages_m1_rev2 import load_rev2
from studies.m0.m1_fix3_checks import (
    base_rate,
    digit_both_readings_problems,
    format_problems,
    grid_wording_problems,
    retry_levels,
    rule_rate,
    shape_mix_problems,
)

OLD = {x.id: x for x in [*lineages_of("M1"), *load_rev2()]}
BATCH1 = {x.id: x for x in load_batch()}


def line(name: str, problems: object) -> None:
    print(f"{name}: {'FAILS-ON-OLD' if problems else 'would pass on old'} -> {str(problems)[:230]}")


def main() -> None:
    # 1. no Retry inside any builder: every old existing lineage and the carried-over shapes
    for lid in ("M1.finite_differences", "M1.recurrence_iterate", "M1.tiered_pricing", "M1.shopping", "M1.speed_distance", "M1.mixture", "M1.percent_change", "M1.tip_split", "M1.average_missing", "M1.clock_duration", "M1.fraction_remainder"):
        line(f"no_retry[{lid}]", retry_levels(OLD.get(lid) or BATCH1[lid]))
    # 2. stated answer format: the 16 existing lineages
    for lid in sorted(x.id for x in lineages_of("M1")):
        line(f"states_format[{lid}]", format_problems(OLD[lid], 5))
    # 3. wording
    line("grid_wording[M1.grid_perimeter_r2]", grid_wording_problems(OLD["M1.grid_perimeter_r2"]))
    line("digit_both_readings[M1.digit_puzzle_r2]", digit_both_readings_problems(OLD["M1.digit_puzzle_r2"]))
    # 4. shortcut tests (the same thresholds as the new tests)
    thresholds = [("M1.mixture", "unweighted_mean", 0.08), ("M1.coins", "value_over_high", 0.06), ("M1.crt_congruence_r2", "largest_mod_remainder", 0.06), ("M1.speed_distance", "sum_speeds_x_mean_hours", 0.05),
                  ("M1.pigeonhole_worst_case_r2", "ignore_caps", 0.12), ("M1.gcd_lcm_r2", "gcd_of_two_smallest", 0.01), ("M1.pythagoras_r2", "memorised_16_scaled", 0.12)]
    for lid, rule, bound in thresholds:
        rates = [round(rule_rate(OLD[lid], rule, lv, 600), 3) for lv in range(7)]
        line(f"rule<={bound}[{lid}:{rule}]", [f"L{lv}:{r}" for lv, r in enumerate(rates) if r > bound])
    for lid, bound in (("M1.mode_tally_r2", 0.06), ("M1.grid_perimeter_r2", 0.12), ("M1.power_remainder_r2", 0.10)):
        bases = [round(base_rate(OLD[lid], lv, 1200), 3) for lv in range(7)]
        line(f"base<={bound}[{lid}]", [f"L{lv}:{b}" for lv, b in enumerate(bases) if b > bound])
    # 5. shape mix: gcd_lcm, division_counting, pigeonhole
    for lid, key, vals in (("M1.gcd_lcm", "ask", {"gcd", "lcm"}), ("M1.division_counting", "shape", {"pallets", "empty_seats"}), ("M1.pigeonhole_worst_case", "goal", {"same", "all"})):
        line(f"shape_mix[{lid}]", shape_mix_problems(BATCH1[lid], key, vals, 800))


if __name__ == "__main__":
    main()
