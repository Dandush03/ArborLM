# ruff: noqa: E501
"""M0 stage I0-a: the known-truth test of the power simulation (ADR-0033 section 9.4, gate 1), SHORT version.

What this default version does: three scenarios (S1, S3, S6) or the machinery checks below, 40 synthetic M0 draws,
300 simulated samples per draw, 4,000 fresh-cluster runs for the known power, a loose tolerance (0.06) and a loose
Monte Carlo bound (0.03). It does NOT cover the registered tolerance 0.03 or the registered Monte Carlo bound 0.01,
which need the long version: ``uv run --locked python -m studies.m0.knowntruth --profile long`` (about 35 s here;
the freeze gate is that run plus the auditor's independent recomputation).

FINDING recorded by these tests: with revision 4's wording the plug-in tau estimate makes the recovered power too low
(conservative direction) in every scenario; S6 (unbalanced, tau = 0) misses even the loose tolerance, and the long run
misses the registered 0.03 in S2, S3 and S6. The S6 test is therefore a strict expected failure, so it turns red if the
behaviour ever changes. With the TRUE tau plugged in, the machinery recovers the known power (the oracle test passes).
Self-checked only.
"""

from __future__ import annotations

import dataclasses
import math
import random
from statistics import fmean

import pytest

from studies.m0 import config as cfgmod
from studies.m0 import knowntruth as kt
from studies.m0 import power as pw

CFG = cfgmod.load()
SC = {s.name: s for s in kt.scenarios_from_config(CFG)}
K = CFG["knowntruth"]
P = kt.PROFILES["short"]


def _short(name: str, tol: float = 0.06) -> kt.ScenarioResult:
    return kt.run_scenario(SC[name], K["clusters"], K["n_items"], P["draws"], P["sims"], P["truth_runs"], K["seed"], tol, P["max_se"])


def test_scenarios_match_review_3_definitions() -> None:
    assert [s.name for s in SC.values()] == ["S1", "S2", "S3", "S4", "S5", "S6"]
    assert (SC["S3"].d, SC["S3"].tau, SC["S3"].sizes, SC["S3"].delta) == (0.30, 0.05, "unbalanced", 0.020)
    assert (SC["S4"].d, SC["S4"].tau, SC["S4"].delta) == (0.02, 0.01, 0.004)
    assert kt.size_pattern("unbalanced", 300).count(16) == 60 and sum(kt.size_pattern("unbalanced", 300)) == 1620
    assert K["tolerance"] == 0.03 and K["max_monte_carlo_se"] == 0.01 and K["clusters"] == 300 and K["n_items"] == 6000


@pytest.mark.parametrize("name", ["S1"])
def test_short_known_truth_passes_in_the_balanced_scenario_at_the_loose_tolerance(name: str) -> None:
    r = _short(name)
    assert r.verdict == "PASS", r


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="FINDING: revision 4's plug-in tau-hat under-recovers the known power in S6 (unbalanced, tau = 0); see studies/m0/NOTES.md")
def test_short_known_truth_s6() -> None:
    assert _short("S6").verdict == "PASS"


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="FINDING: S3 misses the REGISTERED tolerance 0.03 (long run: -0.052; auditor -0.060); the loose 0.06 tolerance hides it")
def test_registered_tolerance_fails_in_s3() -> None:
    r = kt.run_scenario(SC["S3"], K["clusters"], K["n_items"], 150, 300, 6000, K["seed"], K["tolerance"], 1.0)
    assert r.verdict == "PASS", r


def test_the_gate_can_fail_with_a_tight_tolerance_and_with_a_broken_tau_formula(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _short("S1", tol=1e-6).verdict == "FAIL"
    monkeypatch.setattr(pw, "estimate_tau2", lambda v, s_w2, inv_m: max(0.0, v))  # forgets the noise correction
    broken = _short("S1", tol=0.10)
    assert broken.verdict == "FAIL" and broken.difference < -0.3, broken


def test_the_machinery_recovers_the_known_power_when_the_true_tau_is_plugged_in() -> None:
    for name in ("S2", "S6"):
        sc = SC[name]
        rng = random.Random(77)
        got = []
        for i in range(30):
            comp = pw.components(kt.synthetic_m0(sc, 300, rng))
            t2 = sc.tau**2
            lam = tuple(math.sqrt(t2 / (t2 + comp.s_w2 / m)) if t2 > 0 else 0.0 for m in comp.m_g)
            xbar = fmean(comp.mean_g)
            dev = tuple(lam[j] * (comp.mean_g[j] - xbar) for j in range(300))
            got.append(pw.simulate_power(dataclasses.replace(comp, tau2=t2, lam=lam, dev=dev), 6000, [sc.delta], 300, 300, 953301, label=f"o{i}")[sc.delta][0])
        known, _ = kt.truth_power(sc, 300, 6000, 4000, 953301)
        assert abs(fmean(got) - known) < 0.06, (name, fmean(got), known)


def test_inconclusive_when_the_monte_carlo_bound_is_exceeded() -> None:
    r = kt.run_scenario(SC["S1"], 300, 6000, 4, 100, 2000, 953302, 0.5, 0.0001)
    assert r.verdict.startswith("INCONCLUSIVE")


def test_oracle_with_positive_tau_recovers_the_known_power() -> None:
    """Audit R5: S1 and S3 have tau = 0.05, so the shrinkage path (lambda_g > 0) is exercised."""
    for name in ("S1", "S3"):
        sc = SC[name]
        rng = random.Random(78)
        got = []
        for i in range(30):
            comp = pw.components(kt.synthetic_m0(sc, 300, rng))
            t2 = sc.tau**2
            lam = tuple(math.sqrt(t2 / (t2 + comp.s_w2 / m)) for m in comp.m_g)
            assert all(x > 0 for x in lam)
            xbar = fmean(comp.mean_g)
            dev = tuple(lam[j] * (comp.mean_g[j] - xbar) for j in range(300))
            got.append(pw.simulate_power(dataclasses.replace(comp, tau2=t2, lam=lam, dev=dev), 6000, [sc.delta], 300, 300, 953303, label=f"p{i}")[sc.delta][0])
        known, _ = kt.truth_power(sc, 300, 6000, 4000, 953303)
        assert abs(fmean(got) - known) < 0.06, (name, fmean(got), known)


def test_oracle_is_sensitive_to_dropping_the_cluster_deviations_at_high_tau() -> None:
    """Audit follow-up on R5: with tau = 0.10 the between-cluster spread dominates, so a simulation without the cluster
    deviations is far from the known power while the oracle is close to it."""
    sc = kt.Scenario("S7", 0.30, 0.10, "balanced5", 0.015)
    rng = random.Random(79)
    with_dev, without = [], []
    for i in range(20):
        comp = pw.components(kt.synthetic_m0(sc, 300, rng))
        t2 = sc.tau**2
        lam = tuple(math.sqrt(t2 / (t2 + comp.s_w2 / m)) for m in comp.m_g)
        xbar = fmean(comp.mean_g)
        dev = tuple(lam[j] * (comp.mean_g[j] - xbar) for j in range(300))
        full = dataclasses.replace(comp, tau2=t2, lam=lam, dev=dev)
        flat = dataclasses.replace(full, dev=(0.0,) * 300)
        with_dev.append(pw.simulate_power(full, 6000, [sc.delta], 300, 300, 953304, label=f"a{i}")[sc.delta][0])
        without.append(pw.simulate_power(flat, 6000, [sc.delta], 300, 300, 953304, label=f"b{i}")[sc.delta][0])
    known, _ = kt.truth_power(sc, 300, 6000, 4000, 953304)
    assert abs(fmean(with_dev) - known) < 0.06, (fmean(with_dev), known)
    assert abs(fmean(without) - known) > 0.15, (fmean(without), known)
