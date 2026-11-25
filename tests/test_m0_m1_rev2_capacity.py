# ruff: noqa: E501
"""M1 rev2, capacity counted on structure (R-5), demand at the G written. A SAMPLED lower bound (inverse collision probability, m_gates.capacity_one at a smaller sample than the manifest's 20,000);
the lineage-levels that still fail are listed in the manifest, not hidden here: this test pins the demand arithmetic, a set of lineage-levels that pass with margin, and the binomial_choose shortfall."""

from __future__ import annotations

import math

import pytest

from studies.m0.m1_rev2_gates import G_LENIENT, G_WRITTEN, capacity_one, demand

M = 8000


def test_demand_arithmetic_at_the_g_written() -> None:
    # 10 x (ceil(24,000 / G) + 100) on a core level; 10 x 100 on a reserve level
    assert demand(3, G_WRITTEN) == 10 * (math.ceil(24000 / 11) + 100) == 22_820
    assert demand(3, G_LENIENT) == 10 * (math.ceil(24000 / 18) + 100) == 14_340
    assert demand(3, 300) == 1_800
    assert demand(0, G_WRITTEN) == demand(6, G_WRITTEN) == 1_000


@pytest.mark.parametrize(("lid", "levels"), [
    ("M1.crt_congruence_r2", (2, 3, 4, 5)),
    ("M1.digit_puzzle_r2", (1, 2, 3, 4, 5)),
    ("M1.painted_cube_r2", (3, 4, 5)),
    ("M1.gcd_lcm_r2", (2, 3, 4, 5)),
    ("M1.pigeonhole_worst_case_r2", (2, 3, 4, 5)),
    ("M1.grid_perimeter_r2", (1, 2, 3, 4, 5)),
])
def test_widened_and_order_dependent_lineages_pass_the_demand_at_the_g_written_where_claimed(lid: str, levels: tuple[int, ...]) -> None:
    _, rec = capacity_one((lid, M))
    for lv in levels:
        ne = rec[str(lv)]["n_eff"]
        assert ne is None or ne >= demand(lv, G_WRITTEN), (lid, lv, ne)


def test_binomial_choose_r2_still_fails_even_the_g_300_demand_on_structure() -> None:
    _, rec = capacity_one(("M1.binomial_choose_r2", M))
    for lv in (0, 1, 2, 3, 4, 5):
        ne = rec[str(lv)]["n_eff"]
        assert ne is not None and ne < demand(lv, 300), (lv, ne)  # listed in the manifest as not registered at these levels
