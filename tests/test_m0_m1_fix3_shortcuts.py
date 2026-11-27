# ruff: noqa: E501
"""M1 fix round 3, shortcuts removed by construction. Bounds are the measured rates of the new shapes with a margin; the same assertions fail on the pre-fix shapes (m1_fix3_failing_first.py).
They are working checks for this fix round, not registered thresholds."""

from __future__ import annotations

import pytest

from studies.m0.lineages_m1_fix3 import load_all
from studies.m0.m1_fix3_checks import base_rate, rule_rate

ALL = {x.id: x for x in load_all()}


@pytest.mark.parametrize(("lid", "rule", "bound"), [
    ("M1.mixture_r3", "unweighted_mean", 0.08),
    ("M1.coins_r3", "value_over_high", 0.06),
    ("M1.crt_congruence_r3", "largest_mod_remainder", 0.06),
    ("M1.crt_congruence_r3", "drop_last_condition", 0.12),
    ("M1.speed_distance_r3", "sum_speeds_x_mean_hours", 0.05),
    ("M1.pigeonhole_worst_case_r3", "ignore_caps", 0.12),
    ("M1.gcd_lcm_r3", "gcd_of_two_smallest", 0.01),
    ("M1.gcd_lcm_r3", "gcd_of_two_largest", 0.01),
    ("M1.gcd_lcm_r3", "lcm_of_two_largest", 0.01),
    ("M1.gcd_lcm_r3", "lcm_of_first_two_printed", 0.01),
    ("M1.gcd_lcm_r3", "product", 0.01),
    ("M1.median_list_r3", "mode_value", 0.10),
    ("M1.mode_tally_r3", "first_repeated", 0.12),
    ("M1.mode_tally_r3", "most_common_first_half", 0.13),
])
def test_cheap_rule_is_at_chance_level_at_every_level(lid: str, rule: str, bound: float) -> None:
    for lv in range(7):
        assert rule_rate(ALL[lid], rule, lv, 800) <= bound, (lid, rule, lv)


@pytest.mark.parametrize(("lid", "bound"), [("M1.mode_tally_r3", 0.06), ("M1.grid_perimeter_r3", 0.12), ("M1.last_digit_power_r3", 0.10)])
def test_most_frequent_answer_rate_is_low_at_every_level(lid: str, bound: float) -> None:
    for lv in range(7):
        assert base_rate(ALL[lid], lv, 1200) <= bound, (lid, lv)


def test_rules_never_right_by_construction_are_listed_not_hidden() -> None:
    """R-13: a rule that scores exactly 0.00 everywhere is itself a tell. The memorised-triple route of pythagoras is the only rule this round removes to near 0 by construction in a registered shape:
    the gcd and lcm partial rules (which the structure makes impossible, checked exactly in test_m0_m1_fix3_generators) are reported in the manifest with their 0.00, as a known property of the structure."""
    assert rule_rate(ALL["M1.gcd_lcm_r3"], "gcd_of_two_smallest", 4, 500) == 0.0
