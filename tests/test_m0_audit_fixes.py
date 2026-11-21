# ruff: noqa: E501
"""M0 stage I0-a: tests for the implementation defects of docs/reviews/adr-0033-m0-2026-11-20/AUDIT_I0A.md that hold under
either design (B1, R1, R3, R4, R5, R7, C1 to C5). Each test failed before its fix. B2, R2 and R6 are NOT fixed here (they
depend on the design decision or on a separate context) and have no test. Self-checked only."""

from __future__ import annotations

import ast
import random
from pathlib import Path
from statistics import NormalDist

import pytest

from studies.m0 import config as cfgmod
from studies.m0 import ggen
from studies.m0 import outcomes as oc
from studies.m0 import power as pw
from studies.m0 import stats as st

ROOT = Path(__file__).resolve().parents[1]


def test_b1_required_size_search_uses_the_conjunction_count_not_the_per_part_count(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[int] = []
    real = pw.required_size

    def spy(comp, delta, g_e, m_tests, *a, **k):  # type: ignore[no-untyped-def]
        seen.append(m_tests)
        return real(comp, delta, g_e, m_tests, *a, **k)

    monkeypatch.setattr(oc.pw, "required_size", spy)
    r = random.Random(1)
    recs = [st.Rec(f"{c}-{i}", f"c{c}", f"f{c % 2}", {k: int(r.random() < p) for k, p in (("S0", 0.45), ("TQ", 0.7), ("TG", 0.55), ("SIB", 0.6))}) for c in range(30) for i in range(10)]
    part = oc.PartInput("reasoning", "R1", "A", recs, [4] * len(recs), 30)
    oc.analyse_part(part, oc.Roles("S0", ("TQ", "TG"), ("TQ", "TG", "SIB")), cfgmod.load(), b=100, seed=1, sims=20, tests_total=55, m_tests=5)
    assert seen and set(seen) == {55}  # per-test target 1 - 0.2 / 55, not 1 - 0.2 / 5


def _two_teacher_table(seed: int, n_clusters: int = 12) -> st.Table:
    r = random.Random(seed)
    recs = [st.Rec(f"{c}-{i}", f"c{c:02d}", "s", {"T1": int(r.random() < 0.62), "T2": int(r.random() < 0.58)}) for c in range(n_clusters) for i in range(8)]
    return st.Table.from_recs(recs, ["T1", "T2"])


def _t_bound(tab: st.Table, t1: str, t2: str, keep: str) -> float:
    """One-sided t lower bound of U minus the score of teacher ``keep`` (a linear statistic)."""
    u = [max(a, b) for a, b in zip(tab.cols[f"c_{t1}"], tab.cols[f"c_{t2}"], strict=True)]
    lin = [x - y for x, y in zip(u, tab.cols[f"c_{keep}"], strict=True)]
    t = st.Table(tab.clusters, tab.strata, {"lin": lin})
    cl, _ = t.cluster_table(["lin"])
    mean, se, g = st.cluster_robust(cl, 1)
    return mean - st.t_quantile(0.95, g - 1) * se


def test_r1_union_gain_on_the_t_branch_is_the_minimum_over_both_possible_better_teachers() -> None:
    differ = 0
    for seed in range(1, 40):
        tab = _two_teacher_table(seed)
        ug = st.union_gain(tab, "T1", "T2", 100, 400008)
        expect = min(_t_bound(tab, "T1", "T2", "T1"), _t_bound(tab, "T1", "T2", "T2"))
        assert ug.lower.method == "t" and ug.lower.lo == pytest.approx(expect)
        swapped = st.union_gain(_two_teacher_table(seed), "T2", "T1", 100, 400008)
        assert swapped.lower.lo == pytest.approx(ug.lower.lo)  # the order in which the teachers are named does not matter
        s1, s2 = sum(tab.cols["c_T1"]), sum(tab.cols["c_T2"])
        best = "T1" if s1 >= s2 else "T2"
        if _t_bound(tab, "T1", "T2", best) != expect:
            differ += 1
    assert differ > 0  # the test discriminates: the fixed-better-teacher linearisation is not always the minimum


def test_r3_the_s6_expected_failure_only_accepts_an_assertion_failure() -> None:
    import tests.test_m0_knowntruth as kt_tests

    marks = [m for m in kt_tests.test_short_known_truth_s6.pytestmark if m.name == "xfail"]
    assert marks and marks[0].kwargs.get("raises") is AssertionError and marks[0].kwargs.get("strict") is True


def test_r4_the_passes_test_covers_only_scenarios_that_pass_the_registered_tolerance() -> None:
    tree = ast.parse((ROOT / "tests" / "test_m0_knowntruth.py").read_text())
    for fn in tree.body:
        if isinstance(fn, ast.FunctionDef) and fn.name.startswith("test_short_known_truth_passes"):
            params = [d for d in fn.decorator_list if isinstance(d, ast.Call) and getattr(d.func, "attr", "") == "parametrize"]
            vals = [ast.literal_eval(params[0].args[1])] if params else []
            assert vals == [["S1"]], vals
    import tests.test_m0_knowntruth as kt_tests

    assert hasattr(kt_tests, "test_registered_tolerance_fails_in_s3")


def test_r5_oracle_test_covers_a_scenario_with_positive_tau() -> None:
    import tests.test_m0_knowntruth as kt_tests

    assert hasattr(kt_tests, "test_oracle_with_positive_tau_recovers_the_known_power")


def test_r7_config_file_has_the_name_of_adr_0033_section_13() -> None:
    assert cfgmod.CONFIG_PATH.name == "m0_reference_models.toml"
    assert cfgmod.CONFIG_PATH.exists() and not (ROOT / "configs" / "m0_references.toml").exists()


def test_c1_t_quantile_is_exact_at_small_degrees_of_freedom() -> None:
    for df, p, expect in ((1, 0.95, 6.31375), (2, 0.95, 2.91999), (3, 0.95, 2.35336), (6, 0.95, 1.94318), (1, 0.975, 12.7062), (29, 0.975, 2.04523), (299, 0.95, 1.64999)):
        assert st.t_quantile(p, df) == pytest.approx(expect, abs=2e-4), (df, p)
    assert st.t_quantile(0.5, 7) == pytest.approx(0.0, abs=1e-9)
    assert st.t_quantile(0.05, 9) == pytest.approx(-st.t_quantile(0.95, 9))
    assert abs(st.t_quantile(0.99999, 100000) - NormalDist().inv_cdf(0.99999)) < 1e-3


def test_c2_a_stratum_without_residuals_uses_the_residuals_pooled_over_strata() -> None:
    clusters = [("a", [1.0]), ("a", [0.0]), ("b", [1.0, 0.0, 0.0, 0.0, 0.0]), ("b", [0.0, 0.0, 0.0, 0.0, -1.0])]
    comp = pw.components(clusters)
    assert comp.residuals["b"] and comp.residuals["a"] == comp.residuals["b"]
    only_singletons = pw.components([("a", [1.0]), ("a", [0.0])])
    assert only_singletons.residuals["a"] == ()  # nothing to pool: zero noise, the only possibility


def test_c3_stronger_checks_replace_the_weak_ones() -> None:
    # the shrinkage factor, on data with a known positive tau2
    clusters = [("h", [1.0, 1.0, 1.0, 1.0]), ("h", [0.0, 0.0, 0.0, 0.0]), ("h", [-1.0, -1.0, 0.0, -1.0]), ("h", [1.0, 0.0, 1.0, 1.0])]
    c = pw.components(clusters)
    assert c.tau2 > 0.2 and all(0 < lam < 1 for lam in c.lam)
    # required size on data that cannot fail: every difference is zero, so the first rung is reached
    zero = pw.components([("h", [0.0] * 5) for _ in range(40)])
    assert pw.required_size(zero, 0.02, 40, 5, 50, 953401, ladder=(500, 1000))[0] == 500
    # tau interval and confirmation on data with known answers
    assert pw.tau_interval([("h", [0.0] * 5) for _ in range(40)], 100, 953401) == (0.0, 0.0, 0.0)
    assert pw.confirm_power(zero, 500, 0.02, 40, 10, 50, 953401) == (1.0, 0.0)
    r = random.Random(5)
    cl = [("h", [float(r.choice((1, 1, 1, 0)) if i % 2 else r.choice((0, 0, 0, -1))) for _ in range(6)]) for i in range(80)]
    point, lo, hi = pw.tau_interval(cl, 400, 953402)
    assert lo <= point <= hi and point > 0.1


def test_c4_the_same_cluster_id_in_two_strata_is_refused() -> None:
    tab = st.Table(["c1", "c1", "c2"], ["s1", "s2", "s1"], {"x": [1.0, 0.0, 1.0]})
    with pytest.raises(ValueError, match="more than one stratum"):
        tab.cluster_table(["x"])


def test_c5_a_capacity_failure_is_worded_as_not_shown() -> None:
    assert "not shown" in ggen.CAPACITY_FAILURE_MEANING and "cannot" in ggen.CAPACITY_FAILURE_MEANING
