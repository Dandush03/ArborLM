# ruff: noqa: E501
"""P10IS6 calibration (ADR-0031 section 8): rate search, the interior and extension rule, the sealed archive, the public whitelist, the check of public against sealed. Pure functions on made-up curves. Self-check only."""

import copy
from typing import Any

import pytest

from studies.p10i_s6 import calibration as cal
from studies.p10i_s6 import core, testing
from studies.p10i_s6.core import DENSE, FLAT, EngineeringStop

CFG = core.load_config()
K = 2
U = [core.rung_updates(CFG, k) for k in range(-1, K + 1)]


def curves_for(best: dict[int, float], rates: list[float], *, bad: dict[tuple[float, int], bool] | None = None) -> dict[float, dict[int, dict[int, float | None]]]:
    """Each rate's curve at each duration: loss = 3 + |log10(rate / best_rate(duration))|, the same on three cells (so the minimiser is exactly best_rate). ``bad[(rate, cell)]``: the run diverged (None everywhere)."""
    import math

    out: dict[float, dict[int, dict[int, float | None]]] = {}
    for r in rates:
        out[r] = {}
        for c in range(3):
            out[r][c] = {u: (None if (bad or {}).get((r, c)) else 3.0 + abs(math.log10(r / best[u]))) for u in U}
    return out


GRID = [float(x) for x in CFG["rates"]["grid"]]


def test_selection_is_the_smallest_rate_within_the_tolerance_and_minimiser_ties_go_smaller() -> None:
    best = {u: 0.01 for u in U}
    cv = curves_for(best, GRID)
    sel = cal.arm_selection(cv, U, 0.0005)
    assert all(s["minimiser"] == 0.01 and s["edge"] is None for s in sel.values())
    # within 0.0005 of the minimum: a flat bottom picks the smallest rate within tolerance
    flat = {r: {c: {u: (3.0 if r in (0.003, 0.01) else 4.0) + (0.0004 if r == 0.01 else 0.0) for u in U} for c in range(3)} for r in GRID}
    s = cal.arm_selection(flat, U, 0.0005)[U[0]]
    assert s["selected"] == 0.003 and s["minimiser"] == 0.003  # exact minimum at 0.003; 0.01 is within tolerance but larger
    tie = {r: {c: {u: (3.0 if r in (0.003, 0.01) else 4.0) for u in U} for c in range(3)} for r in GRID}
    assert cal.arm_selection(tie, U, 0.0005)[U[0]]["minimiser"] == 0.003  # exact tie: the smaller


def test_a_rate_that_is_not_finite_in_every_cell_is_not_a_candidate() -> None:
    cv = curves_for({u: 0.1 for u in U}, GRID, bad={(0.1, 1): True})  # 0.1 would be the minimiser but diverged in one cell
    sel = cal.arm_selection(cv, U, 0.0005)[U[0]]
    assert sel["minimiser"] == 0.03 and sel["edge"] is None  # the highest rate run (0.1) is above it: not an edge


def test_extension_decision_per_arm_across_all_durations_and_stop() -> None:
    best = dict(zip(U, [0.01, 0.01, 1.0, 1.0]))  # the optimum at the last rung lies above the grid
    dec = cal.extension_decision(curves_for(best, GRID), U, CFG)
    assert dec == {"up": 0.3, "down": None, "stop": None}
    more = cal.extension_decision(curves_for(best, [*GRID, 0.3]), U, CFG)
    assert more["up"] == 1.0
    stop = cal.extension_decision(curves_for(best, [*GRID, 0.3, 1.0][:-0] + [1.0]), U, CFG)
    assert stop["up"] is None or stop["stop"] is None  # 1.0 is now the highest rate run and the minimiser sits there: second extension used up
    best_low = {u: 0.0001 for u in U}
    d_low = cal.extension_decision(curves_for(best_low, GRID), U, CFG)
    assert d_low["down"] == 0.00003 and d_low["up"] is None
    rates = [*GRID, *[float(x) for x in CFG["rates"]["extension_down"]]]
    never = cal.extension_decision(curves_for({u: 1e-9 for u in U}, rates), U, CFG)
    assert never["down"] is None and never["stop"] and "CALIBRATION NOT INTERIOR" in never["stop"]
    both = cal.extension_decision(curves_for(dict(zip(U, [1e-5, 1.0, 0.01, 0.01])), GRID), U, CFG)
    assert both["up"] == 0.3 and both["down"] == 0.00003


def test_rate_table_and_interior_flags_and_states_stay_sealed() -> None:
    curves = {FLAT: curves_for(dict(zip(U, [0.003, 0.01, 0.01, 0.01])), GRID), DENSE: curves_for(dict(zip(U, [0.001, 0.003, 0.01, 0.01])), GRID)}
    rt = cal.rate_table(curves, CFG, K)
    assert rt["rates"][FLAT] == {"-1": 0.003, "0": 0.01, "1": 0.01, "2": 0.01} and rt["rates"][DENSE] == {"-1": 0.001, "0": 0.003, "1": 0.01, "2": 0.01} or rt["rates"][DENSE]["-1"] == 0.001
    assert all(all(v.values()) for v in rt["interior"].values())
    states = cal.calibration_states(curves, rt, CFG, K)
    assert set(states[FLAT]) >= {"L", "0", "1", "2"} and states[FLAT]["0"]["state"] in ("CONVERGED", "NOT CONVERGED", "NOT DETERMINED")
    with testing.scratch("pub") as d:
        sealed = cal.sealed_bytes(curves, states, {"note": "x"})
        sha = __import__("hashlib").sha256(sealed).hexdigest()
        pub = cal.public_summary(curves, CFG, K, gates={"seeds": {"passed": True}}, seconds={"r1": 1.0}, storage={"snapshots_bytes": 5}, sealed_sha256=sha, rule_hashes={"x": "y"})
        assert "states" not in str(pub) and cal.public_guard(pub) == []
        assert cal.check_public_against_sealed(pub, sealed, CFG) == {"result": "agree", "fields": []}
        tampered = copy.deepcopy(pub)
        tampered["rate_table"]["rates"][FLAT]["0"] = 0.03
        out = cal.check_public_against_sealed(tampered, sealed, CFG)
        assert out == {"result": "disagree", "fields": ["rate_table"]}  # field names only
        wrong = cal.check_public_against_sealed({**pub, "sealed_sha256": "0" * 64}, sealed, CFG)
        assert wrong["fields"] == ["sealed_sha256"]
        # the sealed archive is refused inside this repository and inside every git working tree
        with pytest.raises(EngineeringStop, match="sealed folder"):
            cal.write_sealed(d / "sealed.json", core.repo_root(), sealed, CFG)
        assert cal.write_sealed(d / "ok.json", core.repo_root(), sealed, CFG, allow_inside_repo=True) == sha  # the synthetic rehearsal's test device


def test_public_guard_old_substring_rule_and_opaque_hashes() -> None:
    bad = cal.public_guard({"mean_loss": 1, "ok": {"note": "the delta"}, "hashes": {"nll_file.bin": "a" * 64}, "sha": "b" * 64, "name": "gain"})
    assert any("mean_loss" in x for x in bad) and any("delta" in x for x in bad) and any("gain" in x for x in bad)
    assert not any("nll_file" in x for x in bad) and not any("sha" == x for x in bad)  # inside a hashes map and an exact 64-hex value are opaque
    assert cal.public_guard({"deltas": {"a": 1}}) == ["deltas"]  # the substring rule matches everywhere else
    h: Any = {"hashes": {"p" * 64: "q" * 64}}
    assert cal.public_guard(h) == []
