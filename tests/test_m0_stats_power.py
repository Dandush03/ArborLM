# ruff: noqa: E501
"""M0 stage I0-a: paired statistics (section 9.1, 9.2) and the power simulation's pieces (section 9.4).
Self-checked only. Nothing here is a result."""

from __future__ import annotations

import math
import random
from statistics import NormalDist

import pytest

from studies.m0 import power as pw
from studies.m0 import stats as st


def _recs(n_clusters: int, per: int, p: dict[str, float], seed: int, strata: int = 1) -> list[st.Rec]:
    r = random.Random(seed)
    out = []
    for c in range(n_clusters):
        for i in range(per):
            out.append(st.Rec(f"{c}-{i}", f"c{c:03d}", f"s{c % strata}", {k: int(r.random() < v) for k, v in p.items()}))
    return out


def test_t_quantile_matches_published_values() -> None:
    assert abs(st.t_quantile(0.95, 10) - 1.8125) < 2e-3
    assert abs(st.t_quantile(0.975, 29) - 2.0452) < 1e-3
    assert abs(st.t_quantile(0.95, 299) - 1.6498) < 1e-3


def test_point_estimates_and_discordance_are_exact_on_a_hand_table() -> None:
    recs = [st.Rec(str(i), f"c{i % 2}", "s", {"A": a, "B": b}) for i, (a, b) in enumerate([(1, 1), (1, 0), (0, 1), (0, 0), (1, 0), (1, 1)])]
    tab = st.Table.from_recs(recs, ["A", "B"])
    d = st.discordance(tab, "A", "B")
    assert d.share == pytest.approx(3 / 6) and d.a_only == pytest.approx(2 / 6) and d.b_only == pytest.approx(1 / 6)
    iv = st.paired_difference(tab, "A", "B", 200, 400008, False)
    assert iv.estimate == pytest.approx(4 / 6 - 3 / 6) and iv.method == "t"  # 2 clusters: the t branch


def test_bootstrap_is_deterministic_and_covers_a_known_difference() -> None:
    recs = _recs(60, 10, {"A": 0.7, "B": 0.5}, 1)
    t1, t2 = st.Table.from_recs(recs, ["A", "B"]), st.Table.from_recs(recs, ["A", "B"])
    a = st.paired_difference(t1, "A", "B", 2000, 400008, False)
    b = st.paired_difference(t2, "A", "B", 2000, 400008, False)
    assert a == b and a.method == "bootstrap"
    assert a.lo < a.estimate < a.hi
    assert st.paired_difference(t1, "A", "B", 2000, 400008, True).lo > a.lo  # one-sided 5 % bound is above the 2.5 % bound
    assert st.paired_difference(t1, "A", "B", 2000, 123, False) != a  # a different seed gives a different resampling


def test_t_branch_below_thirty_clusters() -> None:
    recs = _recs(12, 20, {"A": 0.8, "B": 0.4}, 2)
    tab = st.Table.from_recs(recs, ["A", "B"])
    iv = st.paired_difference(tab, "A", "B", 1000, 400008, False)
    assert iv.method == "t" and iv.lo < iv.estimate < iv.hi
    one = st.paired_difference(tab, "A", "B", 1000, 400008, True)
    assert one.lo > iv.lo


def test_union_gain_recomputes_the_better_teacher_and_is_never_negative_at_the_point() -> None:
    recs = _recs(50, 10, {"T1": 0.6, "T2": 0.55}, 3)
    tab = st.Table.from_recs(recs, ["T1", "T2"])
    ug = st.union_gain(tab, "T1", "T2", 1000, 400008)
    assert ug.union >= ug.better and ug.gain == pytest.approx(ug.union - ug.better)
    assert ug.lower.one_sided and ug.lower.lo <= ug.gain + 1e-12
    ident = [st.Rec(r.item_id, r.cluster, r.stratum, {"T1": r.correct["T1"], "T2": r.correct["T1"]}) for r in recs]
    g0 = st.union_gain(st.Table.from_recs(ident, ["T1", "T2"]), "T1", "T2", 500, 400008)
    assert g0.gain == 0.0  # identical teachers: no gain


def test_stratified_bootstrap_keeps_stratum_cluster_counts() -> None:
    recs = _recs(40, 5, {"A": 0.5}, 4, strata=4)
    tab = st.Table.from_recs(recs, ["A"])
    cl, spans = tab.cluster_table(["c_A"])
    assert [b - a for _, a, b in spans] == [10, 10, 10, 10]
    tot = st.bootstrap_totals(cl, spans, 50, 400008, "x")
    assert (tot[:, 0] == 200).all()  # every resample has the same number of items when clusters are equal-sized


# ---------------------------------------------------------------- power simulation pieces


def test_components_hand_computed() -> None:
    clusters = [("h", [1.0, 0.0]), ("h", [0.0, 0.0]), ("h", [-1.0, 0.0])]
    c = pw.components(clusters)
    assert c.mean_g == (0.5, 0.0, -0.5) and c.m_g == (2, 2, 2)
    assert c.mu == pytest.approx(0.0) and c.d == pytest.approx(2 / 6)
    assert c.s_w2 == pytest.approx((0.5 + 0.0 + 0.5) / 3)  # pooled within-cluster variance, (m - 1) = 1 each
    assert c.v_between == pytest.approx(0.25)  # variance of the cluster means 0.5, 0, -0.5
    assert c.tau2 == pytest.approx(max(0.0, 0.25 - (1 / 3) * 0.5))
    assert sum(c.dev) == pytest.approx(0.0)  # the simulated population's mean difference is exactly zero
    assert len(c.residuals["h"]) == 6


def test_tau_correction_and_shrinkage_formula() -> None:
    assert pw.estimate_tau2(0.1, 0.3, 0.2) == pytest.approx(0.04)
    assert pw.estimate_tau2(0.01, 0.3, 0.2) == 0.0
    clusters = [("h", [1.0, 0.0, 0.0, 1.0]), ("h", [0.0, 0.0, 0.0, 0.0]), ("h", [-1.0, 0.0, -1.0, 0.0]), ("h", [1.0, -1.0, 0.0, 0.0])]
    c = pw.components(clusters)
    if c.tau2 > 0:
        for i in range(4):
            assert c.lam[i] == pytest.approx(math.sqrt(c.tau2 / (c.tau2 + c.s_w2 / c.m_g[i])))
            assert 0 <= c.lam[i] <= 1


def test_strata_allocation_and_even_spread_of_items() -> None:
    clusters = [("a", [0.0, 1.0])] * 3 + [("b", [0.0, -1.0])] * 6
    c = pw.components(clusters)
    assert pw.allocate_strata(c, 90) == {"a": 30, "b": 60}
    assert pw.allocate_strata(c, 10) == {"a": 3, "b": 7}
    assert float(pw._counts(500, 300).sum()) == 500 and set(pw._counts(500, 300).tolist()) == {1.0, 2.0}


def test_power_is_one_when_nothing_differs_and_collapses_when_everything_differs() -> None:
    same = pw.components([("h", [0.0] * 5) for _ in range(40)])
    assert pw.simulate_power(same, 400, [0.02], 40, 200, 953201)[0.02][0] == 1.0
    r = random.Random(1)
    noisy = pw.components([("h", [float(r.choice((-1, 1))) for _ in range(5)]) for _ in range(40)])
    assert pw.simulate_power(noisy, 400, [0.02], 40, 400, 953201)[0.02][0] < 0.5


def test_power_rises_with_n_and_with_delta_and_is_deterministic() -> None:
    r = random.Random(2)
    comp = pw.components([("h", [float(r.choice((-1, 0, 0, 0, 1))) for _ in range(5)]) for _ in range(100)])
    lo = pw.simulate_power(comp, 500, [0.02, 0.05], 100, 400, 953202)
    hi = pw.simulate_power(comp, 4000, [0.02, 0.05], 100, 400, 953202)
    assert hi[0.02][0] >= lo[0.02][0] and lo[0.05][0] >= lo[0.02][0]
    assert pw.simulate_power(comp, 500, [0.02, 0.05], 100, 400, 953202) == lo


def test_cluster_floor_formula_and_boole_target() -> None:
    r = random.Random(3)
    comp = pw.components([("h", [float(r.choice((0, 1)) if i % 2 else 0) for _ in range(5)]) for i in range(60)])
    assert comp.tau > 0
    n = NormalDist()
    expect = n.cdf(0.03 * math.sqrt(300) / comp.tau - n.inv_cdf(0.95))
    assert pw.cluster_floor(comp, 0.03, 300) == pytest.approx(expect)
    assert pw.cluster_floor(comp, 0.03, 300, tau=0.10) == pytest.approx(n.cdf(0.03 * math.sqrt(300) / 0.10 - n.inv_cdf(0.95)))
    from studies.m0.outcomes import per_test_target

    assert per_test_target(0.8, 55) == pytest.approx(1 - 0.2 / 55)


def test_required_size_walks_the_ladder_and_reports_none_when_unreachable() -> None:
    r = random.Random(4)
    easy = pw.components([("h", [float(r.choice((0, 0, 0, 0, 0, 0, 0, 0, 0, 1))) for _ in range(5)]) for _ in range(60)])
    n, tried = pw.required_size(easy, 0.05, 60, 5, 100, 953203, ladder=(500, 1000))
    assert tried and (n is None or n in (500, 1000))
    hard = pw.components([("h", [float(r.choice((-1, 1))) for _ in range(5)]) for _ in range(60)])
    n2, tried2 = pw.required_size(hard, 0.02, 60, 5, 100, 953203, ladder=(500, 1000))
    assert n2 is None and len(tried2) == 2


def test_tau_interval_and_confirmation_run_and_are_ordered() -> None:
    r = random.Random(5)
    cl = [("h", [float(r.choice((-1, 0, 0, 1))) for _ in range(5)]) for _ in range(80)]
    point, lo, hi = pw.tau_interval(cl, 300, 953204)
    assert lo <= hi and point >= 0
    comp = pw.components(cl)
    p, se = pw.confirm_power(comp, 500, 0.05, 80, 20, 200, 953204)
    assert 0 <= p <= 1 and se >= 0
