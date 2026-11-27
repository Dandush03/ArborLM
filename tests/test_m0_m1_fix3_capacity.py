# ruff: noqa: E501
"""M1 fix round 3, capacity (R-5, R-10, R-11). Replaces the rev2 tests that were tautological (demand arithmetic against itself, 'passes where claimed' at a sample too small to fail, a pinned failure).
The checks here: the estimator is validated on a distribution of known support; exact (enumerated) supports are compared with the demand; sampled n_eff is cross-checked against the analytic value;
the old parameter spaces are shown to fall below the demand; the cluster evaluation is unit-tested on synthetic data; and the measured report, when present, is pinned."""

from __future__ import annotations

import json
import math
import random
from pathlib import Path
from typing import Any

import pytest

from studies.m0.core import build_item, stream
from studies.m0.lineages_m1_fix3 import NOT_REGISTERED, load_all
from studies.m0.m1_fix3_gates import canon_key, demand, evaluate, exact_support

ROOT = Path(__file__).resolve().parents[1]
ALL = {x.id: x for x in load_all()}


def n_eff_of(keys: list[str]) -> float:
    from collections import Counter

    c = Counter(keys)
    pairs = sum(v * (v - 1) // 2 for v in c.values())
    m = len(keys)
    return m * (m - 1) / (2 * pairs)


def test_demand_is_the_lead_formula_written_out_by_hand() -> None:
    assert demand(11) == 10 * (364 + 1819 + 100) == 22830
    assert demand(10) == 10 * (400 + 2000 + 100) == 25000


def test_estimator_recovers_a_known_support() -> None:
    rng = random.Random(411301)
    keys = [str(rng.randrange(5000)) for _ in range(30000)]
    assert abs(n_eff_of(keys) - 5000) / 5000 < 0.1
    # a skewed distribution has a SMALLER n_eff than its support (the reason n_eff is a lower bound)
    skew = [str(int(rng.random() ** 3 * 5000)) for _ in range(30000)]
    assert n_eff_of(skew) < 0.6 * 5000


EXACT = exact_support()
SHARE_G10 = {"rectangle": 25000 // 7, "consecutive": 25000 // 7, "ages": 25000 // 7, "coins": 25000 // 7, "fraction_remainder": 25000 // 4, "tip_split": 25000 // 4, "arithmetic_series": 25000 // 2,
             "prime_factors": 25000, "gcd_lcm": 25000, "finite_differences": 25000, "slot_permutations": 25000}


@pytest.mark.parametrize("name", sorted(SHARE_G10))
def test_exact_support_reaches_the_equal_share_of_the_demand_at_every_level(name: str) -> None:
    for lv in range(7):
        assert EXACT[str(lv)][name] >= SHARE_G10[name], (name, lv, EXACT[str(lv)][name])


def test_quadratic_area_mixture_reaches_the_demand_on_its_exact_class_supports() -> None:
    """Weights: rect_area and product share the class 'prod' (probability 1/2), rect_perimeter and squares 1/4 each; the classes have the same support N (the (x, d) pairs)."""
    for lv in range(7):
        n = EXACT[str(lv)]["quadratic_area_prod_class"]
        assert 1 / ((0.25 + 0.0625 + 0.0625) / n) >= 25000, (lv, n)


def test_rectangle_sampled_n_eff_matches_the_analytic_mixture_value() -> None:
    lin = ALL["M1.rectangle_r3"]
    for lv in (0, 3):
        rng = stream(411302, "rect-cap", str(lv))
        keys = [canon_key(lin.id, build_item(lin, lv, rng, "A", "c").structured) for _ in range(30000)]
        n1, n2 = (59 + 10 * lv) * 11, (59 + 10 * lv) * 60
        analytic = 1 / (0.3**2 / n1 + 0.7**2 / n2)
        assert abs(n_eff_of(keys) - analytic) / analytic < 0.12, (lv, n_eff_of(keys), analytic)


def test_the_old_parameter_spaces_were_below_the_equal_share_and_the_new_ones_are_not() -> None:
    """Old spaces counted from the old ranges (lineages_m1.py): rectangle (w 2..20+5L, k 2..4+L//2), consecutive (a -20..200+100L, step 1 or 2 from level 2), fraction_remainder (a, b in 2..6, n = a b j, j 1..20+5L),
    (ages and tip_split are NOT listed: their raw parameter counts exceed the equal share at some levels; the audit measured them failing through the retry's non-uniform draws, so a support count would not show it)."""
    for lv in range(7):
        old = {
            "rectangle": (19 + 5 * lv) * (3 + lv // 2),
            "consecutive": (221 + 100 * lv) * (2 if lv >= 2 else 1),
            "fraction_remainder": 25 * (20 + 5 * lv),
        }
        for name, support in old.items():
            assert support < SHARE_G10[name], (name, lv, support)  # the old space could not meet the equal share (the new test fails on it)
            assert EXACT[str(lv)][name] >= SHARE_G10[name]


def test_not_registered_lineages_are_exactly_the_three_that_failed_and_binomial_fails_on_enumeration() -> None:
    assert set(NOT_REGISTERED) == {"M1.pythagoras_r3", "M1.binomial_choose_r3", "M1.digit_puzzle_r3"}
    assert all(len(v) > 200 for v in NOT_REGISTERED.values())
    for lv in (0, 1, 2):
        assert EXACT[str(lv)]["binomial_choose"] < 2500


def test_pythagoras_space_is_sparse_by_exact_enumeration() -> None:
    def count(h: int) -> int:
        n, m = 0, 2
        while m * m + 1 <= h:
            for k in range(1, m):
                if (m - k) % 2 and math.gcd(m, k) == 1 and m * m + k * k <= h:
                    n += h // (m * m + k * k)
            m += 1
        return n

    assert count(400) == 294 and count(2000) == 1981
    assert 3.57 * count(3200) < 22830  # the mixture of five shapes needs ~ 6,400 triangles even for the lead's demand; 3,200 allows 3,414


def _cap(n_eff: float) -> dict[str, Any]:
    return {"M": 30000, "D": 1, "pairs": 1, "n_eff": n_eff, "f1": 0, "f2": 0, "chao1": round(n_eff), "sec": 0.0}


def test_cluster_evaluation_separates_the_mixture_basis_from_the_equal_share_basis() -> None:
    big, small = 1_000_000.0, 3_000.0
    cap: dict[str, Any] = {"levels": {"M1.linear_equation_r3": {str(lv): _cap(big) for lv in range(7)}, "M1.rectangle_r3": {str(lv): _cap(small) for lv in range(7)},
                      "M1.ages_r3": {str(lv): _cap(big) for lv in range(7)}, "M1.consecutive_r3": {str(lv): _cap(big) for lv in range(7)},
                      "M1.average_missing_r3": {str(lv): _cap(big) for lv in range(7)}, "M1.pipes_work_r3": {str(lv): _cap(big) for lv in range(7)}, "M1.coins_r3": {str(lv): _cap(big) for lv in range(7)}}, "m": 30000}
    rep = evaluate(cap, {})
    row = rep["clusters"]["S1_linear_solve"]
    assert row["fails_G=11"]["mixture"] == []  # one weak member is hidden by the mixture formula
    assert row["fails_G=11"]["equal_share"] == list(range(7))  # but it cannot supply 1 / 7 of the demand on its own (3,000 x 7 = 21,000 < 22,830)
    cap["levels"]["M1.rectangle_r3"] = {str(lv): _cap(200.0) for lv in range(7)}
    assert evaluate(cap, {})["clusters"]["S1_linear_solve"]["fails_G=11"]["mixture"] == list(range(7))


def test_measured_report_when_present_shows_every_registered_cluster_passing_both_bases() -> None:
    p = ROOT / "studies" / "m0" / "manifests" / "m1_fix3_capacity.json"
    if not p.exists():
        pytest.skip("capacity manifest not written yet")
    rep = json.loads(p.read_text())["report"]
    assert rep["demand"]["G=11"] == 22830 and rep["demand"]["G=10"] == 25000
    assert len(rep["clusters"]) == 20
    for name, row in rep["clusters"].items():
        for g in ("G=11", "G=10"):
            assert row[f"fails_{g}"]["mixture"] == [] and row[f"fails_{g}"]["chao1_sum"] == [], (name, g, row[f"fails_{g}"])
    assert not any("pythagoras" in c or "digit_puzzle" in c for c in rep["clusters"])
