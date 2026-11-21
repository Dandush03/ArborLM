# ruff: noqa: E501
"""P10IS6 labels and analysis on synthetic registries with answers worked out by hand (ADR-0031 sections 9 to 12). Self-check only."""

import copy
import random
from dataclasses import replace
from typing import Any

import pytest

from studies.p10i_s6 import analysis, core, labels, synthetic
from studies.p10i_s6.core import DENSE, FLAT, EngineeringStop
from studies.p10i_s6.synthetic import ArmSpec, Spec

CFG = core.load_config()
TH = core.Thresholds.from_config(CFG)
K = 4


def gains(start: float, deltas: list[float]) -> dict[int, float]:
    g = {-1: start}
    for k, d in enumerate(deltas):
        g[k] = g[k - 1] + d
    return g


def run(spec: Spec, *, k_max: int = K, cells: int = 27) -> dict[str, Any]:
    reg = synthetic.registry(CFG, spec)
    return analysis.analyse(reg, synthetic.rate_table(k_max), CFG, k_max=k_max, bitwise=True, cells=cells)


def pair(d_deltas: list[float], lead: list[float], *, d_start: float = 0.10, drun_d: list[float] | None = None, drun_f: list[float] | None = None, cell_flat: dict[int, list[float]] | None = None, **kw: Any) -> Spec:
    """Dense gains from d_deltas; flat gain at rung k = dense gain + lead[k] (and at rung -1 + lead[0] as well so that the flat deltas are the dense deltas plus the lead's changes)."""
    gd = gains(d_start, d_deltas)
    gf = {k: gd[k] + (lead[k] if k >= 0 else lead[0]) for k in gd}
    drd = {k: d for k, d in enumerate(drun_d or d_deltas)}
    drf = {k: d for k, d in enumerate(drun_f or [gf[k] - gf[k - 1] for k in range(K + 1)])}
    return Spec(ArmSpec(gf, drf, cell_flat or {}), ArmSpec(gd, drd), p_used=lambda k, c: 0.08, x_mean=lambda k, c: 0.08, **kw)


SMALL = [0.0005] * 5
BIG = [0.02] * 5


def label_of(res: dict[str, Any]) -> str:
    return str(res["line_p"]["base_label"])


# ------------------------------------------------------------------------------------------------ rows of section 12.3
def test_row4_persists_with_dependence_and_trend() -> None:
    res = run(pair(SMALL, [0.02] * 5))
    assert res["k_star"] == 0 and res["reading_rung"] == 0
    assert res["line_p"]["row"] == 4 and label_of(res) == "PERSISTS AT CONVERGENCE"
    assert "ONE DOUBLING" not in res["line_p"]["label"]
    assert res["d_flat"]["label"] == "DEPENDENT" and res["line_p"]["dependence_qualified"] is True
    assert res["trend"]["tag"] == "LEAD HELD AT EVERY RUNG" and res["trend"]["text"].endswith(labels.TAG_SENTENCE)
    assert [res["per_rung"][str(k)]["class"] for k in range(5)] == ["M-AHEAD"] * 5
    assert res["j_dagger"] == 4  # the dense gain rises every rung: the lowest L is the last; tie rule not needed


def test_row3_ordering_not_stable_and_lost_tag() -> None:
    res = run(pair(SMALL, [0.02, 0.02, 0.0, 0.0, 0.0]))
    assert res["k_star"] == 0 and res["line_p"]["row"] == 3
    assert [res["per_rung"][str(k)]["class"] for k in range(5)] == ["M-AHEAD", "M-AHEAD", "LEVEL", "LEVEL", "LEVEL"]
    assert "(M-AHEAD, M-AHEAD, LEVEL, LEVEL, LEVEL)" in res["line_p"]["label"]
    assert res["trend"]["tag"] == "LEAD LOST BY RUNG 2" and res["trend"]["order"] == 3


def test_row5_level_row6_dense_ahead_row7_undecided() -> None:
    assert label_of(run(pair(SMALL, [0.0] * 5))) == "LEVEL AT CONVERGENCE"
    res6 = run(pair(SMALL, [-0.02] * 5))
    assert res6["line_p"]["row"] == 6 and label_of(res6) == "DENSE AHEAD AT CONVERGENCE"
    # six cells (one in each of six parents) have Q = -0.001, the other 21 have +0.0075: mean 0.0056 >= 0.005, 21 positive cells < 22: neither M-AHEAD nor LEVEL
    neg = [0, 3, 6, 9, 12, 15]
    cell = {k: [0.0085 if c in neg else 0.0 for c in range(27)] for k in range(-1, 5)}
    res7 = run(pair(SMALL, [0.0075] * 5, cell_flat=cell))
    assert [res7["per_rung"][str(k)]["class"] for k in range(5)] == ["UNDECIDED"] * 5
    assert res7["line_p"]["row"] == 7 and label_of(res7) == "LEAD NOT ESTABLISHED AT CONVERGENCE"


def test_k_star_one_doubling_when_only_the_last_rung_is_converged() -> None:
    res = run(pair([0.02, 0.02, 0.02, 0.02, 0.0005], [0.02] * 5))
    assert res["k_star"] == 4 and res["line_p"]["row"] == 4
    assert res["line_p"]["label"].startswith("PERSISTS AT CONVERGENCE (ONE DOUBLING OF EVIDENCE)")


def test_rows_8_to_12() -> None:
    # 8: dense converged (rungs 3 and 4), memory still improving, memory far ahead at rung 4
    gd = [0.02, 0.02, 0.02, 0.0005, 0.0005]
    spec = pair(gd, [0.05] * 5)
    spec.flat = ArmSpec(gains(0.10 + 0.05, [0.02] * 5), {k: 0.02 for k in range(5)})  # the memory improves by 0.02 per rung from a higher start
    res = run(spec)
    assert res["k_star"] is None and res["line_p"]["row"] == 8 and label_of(res) == "MEMORY AHEAD (DENSE CONVERGED, MEMORY STILL IMPROVING)"
    assert "ONE DOUBLING" not in res["line_p"]["label"]  # converged at rung 3 as well
    # 8 with only one doubling of evidence: dense converged at rung 4 only
    spec = pair([0.02] * 4 + [0.0005], [0.05] * 5)
    spec.flat = ArmSpec(gains(0.15, [0.02] * 5), {k: 0.02 for k in range(5)})
    res = run(spec)
    assert res["line_p"]["row"] == 8 and "STILL IMPROVING) (ONE DOUBLING OF EVIDENCE) [" in res["line_p"]["label"]
    # 9: memory converged, dense still improving and ahead
    spec = pair([0.02] * 5, [-0.05] * 5)
    spec.flat = ArmSpec(gains(0.05, [0.02, 0.02, 0.02, 0.0005, 0.0005]), {0: 0.02, 1: 0.02, 2: 0.02, 3: 0.0005, 4: 0.0005})
    res = run(spec)
    assert res["line_p"]["row"] == 9 and label_of(res) == "DENSE AHEAD (MEMORY CONVERGED, DENSE STILL IMPROVING)"
    # 10: dense still improving, memory converged, but the memory is not behind: row 9 does not apply
    spec = pair([0.02] * 5, [0.02] * 5)
    spec.flat = ArmSpec(gains(0.139, [0.02, 0.02, 0.02, 0.0005, 0.0005]), {0: 0.02, 1: 0.02, 2: 0.02, 3: 0.0005, 4: 0.0005})
    res = run(spec)
    assert res["line_p"]["row"] == 10 and label_of(res) == "CONVERGENCE NOT REACHED (DENSE STILL IMPROVING)"
    # 11: memory still improving, dense converged, class at rung 4 not M-AHEAD (level): row 8 does not apply
    spec = pair([0.02, 0.02, 0.02, 0.0005, 0.0005], [0.0] * 5)
    spec.flat = ArmSpec(gains(0.061, [0.02] * 5), {k: 0.02 for k in range(5)})
    res = run(spec)
    assert res["per_rung"]["4"]["class"] == "LEVEL"
    assert res["line_p"]["row"] == 11 and label_of(res) == "CONVERGENCE NOT REACHED (MEMORY STILL IMPROVING)"
    # 12
    res = run(pair(BIG, [0.01] * 5))
    assert res["line_p"]["row"] == 12 and label_of(res) == "CONVERGENCE NOT REACHED (BOTH STILL IMPROVING)"
    assert res["trend"]["tag"] == "LEAD HELD AT EVERY RUNG" and "an arm is still improving per doubling by at least the size of the lead" in res["trend"]["lead_sentence"]
    assert res["line_p"]["label"].count("[") == 1  # the registered trend line sits under every label of rows 3-12


def test_delta_run_condition_blocks_convergence() -> None:
    """Section 9.1: the envelope can flatten while the run still improves; both conditions are needed."""
    res = run(pair(SMALL, [0.02] * 5, drun_d=[0.02] * 5))  # the dense run's own curve still falls by 0.02 per doubling
    assert res["per_rung"]["4"]["convergence"][DENSE] == "NOT CONVERGED" and res["per_rung"]["4"]["convergence"][FLAT] == "CONVERGED"
    assert label_of(res) == "CONVERGENCE NOT REACHED (DENSE STILL IMPROVING)"


# ------------------------------------------------------------------------------------------------ rows 1 and 2 and every cause
@pytest.mark.parametrize(
    "kw,cause_id",
    [({"base_nonfinite": frozenset({2})}, 1), ({"nonfinite_replay": frozenset({(DENSE, 1, 3)})}, 2), ({"base_bad_replay": frozenset({1})}, 1), ({"bad_disabled": frozenset({(FLAT, 2, 5)})}, 2), ({"bad_replay": frozenset({(DENSE, 0, 7)})}, 2), ({"failed": frozenset({(DENSE, 3, 4)})}, 3)],
)
def test_row1_causes(kw: dict[str, Any], cause_id: int) -> None:
    res = run(pair(SMALL, [0.02] * 5, **kw))
    assert res["line_p"]["row"] == 1 and res["line_p"]["label"].startswith("NOT EVALUABLE (") and cause_id in res["line_p"]["cause_ids"]
    assert res["trend"]["tag"] == "TREND NOT DETERMINED"


def test_row1_cause4_dense_adds_nothing() -> None:
    spec = pair([0.0001] * 5, [0.0001] * 5, d_start=0.002)  # Cd(R) at rung 0 about 0.0021 < 0.005
    res = run(spec)
    assert res["line_p"]["cause_ids"] == [4] and res["line_p"]["row"] == 1


def test_row2_memory_failed_cell_and_nonfinite_enabled() -> None:
    res = run(pair(SMALL, [0.02] * 5, failed=frozenset({(FLAT, 4, 0)})))
    assert res["line_p"]["row"] == 2 and label_of(res) == "MEMORY UNSTABLE (FAILED CELLS)" and res["trend"]["tag"] == "TREND NOT DETERMINED"
    assert res["per_rung"]["4"]["L"][FLAT] is None and res["per_rung"]["4"]["convergence"][FLAT] == "NOT DETERMINED"
    res = run(pair(SMALL, [0.02] * 5, nonfinite_enabled=frozenset({(FLAT, 1, 3)})))
    assert res["line_p"]["row"] == 2  # a non-finite enabled NLL at a snapshot a rule reads is a failed cell
    assert res["per_rung"]["1"]["delta"][FLAT] is None and res["per_rung"]["2"]["delta"][FLAT] is None


def test_item_error_and_missing_records_refuse() -> None:
    spec = pair(SMALL, [0.02] * 5)
    reg = synthetic.registry(CFG, spec)
    bad = copy.deepcopy(reg)
    bad[core.run_key(FLAT, synthetic.RATES_FLAT[1], 3)] = {"status": "item_error"}
    with pytest.raises(EngineeringStop, match="ITEM ERRORS"):
        analysis.analyse(bad, synthetic.rate_table(K), CFG, k_max=K, bitwise=True)
    missing = {k: v for k, v in reg.items() if k != core.nll_key(DENSE, synthetic.RATES_DENSE[2], 8, core.rung_updates(CFG, 2), core.READ_ENABLED)}
    with pytest.raises(EngineeringStop, match="INCOMPLETE REGISTRY"):
        analysis.analyse(missing, synthetic.rate_table(K), CFG, k_max=K, bitwise=True)


def test_two_rungs_swapped_changes_the_result() -> None:
    """A case where two rungs' records are swapped: the analysis must not be blind to it."""
    spec = pair(SMALL, [0.02, 0.02, 0.0, 0.0, 0.0])
    reg = synthetic.registry(CFG, spec)
    good = analysis.analyse(reg, synthetic.rate_table(K), CFG, k_max=K, bitwise=True)
    swapped = dict(reg)
    for c in range(27):
        for read in (core.READ_ENABLED, core.READ_REPLAY):
            a = core.nll_key(FLAT, synthetic.RATES_FLAT[0], c, core.rung_updates(CFG, 0), read)
            b = core.nll_key(FLAT, synthetic.RATES_FLAT[2], c, core.rung_updates(CFG, 2), read)
            swapped[a], swapped[b] = reg[b], reg[a]
    other = analysis.analyse(swapped, synthetic.rate_table(K), CFG, k_max=K, bitwise=True)
    assert good["line_p"]["label"].startswith("ORDERING NOT STABLE AFTER CONVERGENCE (M-AHEAD, M-AHEAD, LEVEL, LEVEL, LEVEL)") and good["trend"]["tag"] == "LEAD LOST BY RUNG 2"
    # worked by hand: the memory's rung-0 value becomes its rung-2 value (lead 0) and vice versa, so the classes become LEVEL, M-AHEAD, M-AHEAD, LEVEL, LEVEL
    assert [other["per_rung"][str(k)]["class"] for k in range(5)] == ["LEVEL", "M-AHEAD", "M-AHEAD", "LEVEL", "LEVEL"]
    assert other["line_p"]["label"] != good["line_p"]["label"] and other["trend"]["tag"] != good["trend"]["tag"]  # the known-answer assertions above FAIL on the swapped records


# ------------------------------------------------------------------------------------------------ D[FLAT], harm, collapsed
def test_d_flat_rows_collapsed_and_harm() -> None:
    base = pair(SMALL, [0.02] * 5)
    res = run(base)
    assert res["d_flat"]["label"] == "DEPENDENT"
    low = pair(SMALL, [0.02] * 5)
    low.p_used = lambda k, c: 0.004  # below 0.005 and below 0.5 C
    assert run(low)["d_flat"]["label"] == "CAPACITY WITHOUT DEMONSTRATED DEPENDENCE" and run(low)["d_flat"]["failing"] == ["F2"]
    xl = pair(SMALL, [0.02] * 5)
    xl.x_mean = lambda k, c: 0.004
    assert run(xl)["d_flat"]["failing"] == ["F3"]
    nocap = pair([0.0005] * 5, [0.0] * 5, d_start=0.0)
    nocap.flat = ArmSpec(gains(0.0, [0.0005] * 5), {k: 0.0005 for k in range(5)})  # C about 0.001..0.0025 < 0.005 and Cd likewise: cause 4, and F1 fails
    assert run(nocap)["d_flat"]["label"] == "NO CAPACITY"
    col = pair(SMALL, [0.02] * 5)
    col.used_slots = lambda k, c: 1 if c in (4, 5) else 300
    r = run(col)
    assert r["collapsed_cells"] == [4, 5]  # COLLAPSED cells fail F2
    assert r["d_flat"]["conditions"]["F2"]["cells"] == 25
    nf = pair(SMALL, [0.02] * 5)
    nf.nonfinite_draw = frozenset({(0, 3)})
    assert run(nf)["d_flat"]["conditions"]["F2"]["cells"] == 26  # one cell fails its condition; the mean condition is false then
    assert run(nf)["d_flat"]["conditions"]["F2"]["ok"] is False
    # harm figures: strict ">"
    harm = pair(SMALL, [0.02] * 5)
    harm.p_used = lambda k, c: 0.5  # H_used = H + 0.5 is above B in cells where C < 0.5
    h = run(harm)["harm"]["0"]["H_used"]
    assert h["cells_worse_than_base"] == 27 and h["mean_B_minus"] < 0


def test_r16_three_readings_and_floor() -> None:
    assert run(pair(SMALL, [0.02] * 5))["r16"]["label"] == "REPLICATED AT 16,384"
    within = run(pair(SMALL, [0.002] * 5))["r16"]
    assert within["label"] == "NOT REPLICATED (WITHIN TOLERANCE)"
    assert run(pair(SMALL, [-0.02] * 5))["r16"]["label"] == "NOT REPLICATED (otherwise)"
    absent = run(pair(SMALL, [0.002] * 5))
    assert absent["trend"]["tag"].startswith("LEAD ABSENT AT RUNG 0") and absent["trend"]["order"] == 2
    assert run(pair([0.0001] * 5, [0.0] * 5, d_start=0.002))["r16"]["label"] == "NOT EVALUABLE"


def test_trend_tags_every_row() -> None:
    def tag(lead: list[float]) -> dict[str, Any]:
        return run(pair(BIG, lead))["trend"]

    assert tag([0.03, 0.025, 0.02, 0.015, 0.01])["tag"] == "LEAD SHRINKING"
    assert tag([0.01, 0.015, 0.02, 0.025, 0.03])["tag"] == "LEAD GROWING"
    assert tag([0.02] * 5)["tag"] == "LEAD HELD AT EVERY RUNG"
    t = tag([0.02, 0.0, 0.02, 0.02, 0.02])
    assert t["tag"] == "NOT MONOTONE" and t["order"] == 4
    t = tag([0.02, 0.02, 0.02, 0.0, 0.0])
    assert t["tag"] == "LEAD LOST BY RUNG 3"
    t = tag([0.0, 0.02, 0.02, 0.02, 0.02])
    assert t["order"] == 2
    t = tag([0.02, 0.02, 0.02, 0.02, 0.0])
    assert t["tag"] == "LEAD LOST BY RUNG 4"
    for lead in ([0.03, 0.025, 0.02, 0.015, 0.01], [0.02] * 5):
        assert tag(lead)["text"].endswith(labels.TAG_SENTENCE) and "Δ = " in tag(lead)["text"]


def test_j_dagger_exact_tie_takes_the_larger_rung_and_q_dagger_clause_can_block() -> None:
    assert labels.j_dagger({0: 3.0, 1: 2.5, 2: 2.5, 3: 2.6, 4: 2.7}, 4) == 2
    assert labels.j_dagger({0: 3.0, 1: 2.5, 2: 2.5, 3: 2.5, 4: 2.5}, 4) == 4
    assert labels.j_dagger({0: 3.0, 1: None, 2: 2.5, 3: 2.5, 4: 2.5}, 4) is None
    # the dense arm at its best rung is rung 2 (it gets worse afterwards); the memory at rung 3 is ahead of the dense arm's rung 3 but not of its best rung 2
    gd = {-1: 0.10, 0: 0.12, 1: 0.14, 2: 0.16, 3: 0.14, 4: 0.14}
    gf = {k: gd[k] + 0.006 for k in gd}
    spec = Spec(ArmSpec(gf, {k: 0.0 for k in range(5)}), ArmSpec(gd, {k: 0.0 for k in range(5)}), p_used=lambda k, c: 0.08, x_mean=lambda k, c: 0.08)
    res = run(spec)
    assert res["j_dagger"] == 2
    assert res["per_rung"]["3"]["class"] == "UNDECIDED"  # Q(3) = 0.006 >= 0.005 but Q-dagger(3) = (B - 0.16) - (B - 0.146) = -0.014
    assert res["per_rung"]["2"]["class"] == "M-AHEAD"


# ------------------------------------------------------------------------------------------------ boundary and arithmetic
def test_every_comparison_is_as_written_at_the_boundary() -> None:
    th = replace(TH, effect=0.125, dense_floor=0.125, epsilon=0.125)  # exact binary fractions: the boundary is reached exactly
    q = [0.125] * 27
    assert labels.rung_class(q, q, th) == "M-AHEAD"  # mean >= 0.125
    assert labels.rung_class([x - 2**-40 for x in q], q, th) == "LEVEL"  # just below the margin on both clauses: not M-AHEAD, and inside the level band
    assert labels.rung_class([-0.125] * 27, [-0.125] * 27, th) == "D-AHEAD"  # mean <= -0.125
    assert labels.rung_class([0.0] * 27, [0.0] * 27, th) == "LEVEL"
    assert labels.rung_class([0.125 - 2**-40] * 27, [0.125] * 27, th) == "LEVEL"  # just below the margin
    assert labels.convergence_state(0.125, 0.0, th.epsilon) == "NOT CONVERGED"  # delta < eps, strict
    assert labels.convergence_state(0.125 - 2**-40, 0.125 - 2**-40, th.epsilon) == "CONVERGED"
    assert labels.convergence_state(-1.0, -1.0, th.epsilon) == "CONVERGED"  # a rise counts as below eps
    assert labels.convergence_state(None, 0.0, th.epsilon) == "NOT DETERMINED"
    cells22 = [-0.2 if c in (2, 5, 8, 11, 14) else 0.2 for c in range(27)]  # 22 of 27 positive cells, every parent mean positive
    th2 = replace(TH, effect=0.0)
    assert labels.held(cells22, th2) is True
    assert labels.held([-0.2 if c in (2, 5, 8, 11, 14, 17) else 0.2 for c in range(27)], th2) is False
    p8 = [0.2] * 24 + [-0.9] * 3  # parents: 8 positive (three cells each), the ninth negative
    assert labels.held(p8, replace(TH, effect=0.0, min_cells=21)) is True and labels.held(p8, replace(TH, effect=0.0, min_cells=21, min_parents=9)) is False


def test_means_use_python_float_sum_in_cell_order() -> None:
    v = [0.1, 0.2, 0.3] * 9
    assert labels.mean_of(v) == sum(v) / 27
    assert labels.parent_means(v)[0] == sum([0.1, 0.2, 0.3]) / 3  # builtin sum (compensated since Python 3.12), as ruling G5 says
    assert labels.mean_of([1.0, None]) is None


# ------------------------------------------------------------------------------------------------ an independent oracle on random registries
def oracle(reg: dict[str, Any], k_max: int, n: int) -> tuple[str, int | None]:
    """A second, deliberately naive implementation of rows 1 to 12 (no cause or failure paths): returns (base label, K*)."""
    th = TH
    u = {k: core.rung_updates(CFG, k) for k in range(-1, k_max + 1)}
    rf, rd = synthetic.RATES_FLAT, synthetic.RATES_DENSE

    def val(arm: str, k: int, c: int, at: int) -> float:
        rate = (rf if arm == FLAT else rd)[k]
        return float(reg[core.nll_key(arm, rate, c, at, core.READ_ENABLED)])

    def mean(xs: list[float]) -> float:
        t = 0.0
        for x in xs:
            t += x
        return t / len(xs)

    L = {a: {k: mean([val(a, k, c, u[k]) for c in range(n)]) for k in range(-1, k_max + 1)} for a in (FLAT, DENSE)}
    conv = {a: {k: (L[a][k - 1] - L[a][k] < th.epsilon) and (mean([val(a, k, c, u[k - 1]) for c in range(n)]) - L[a][k] < th.epsilon) for k in range(0, k_max + 1)} for a in (FLAT, DENSE)}
    kstar = None
    for k in range(0, k_max + 1):
        if all(conv[a][j] for a in (FLAT, DENSE) for j in range(k, k_max + 1)):
            kstar = k
            break
    jd = min(range(0, k_max + 1), key=lambda k: (L[DENSE][k], -k))
    B = [baseline_(c) for c in range(n)]

    def cls(k: int) -> str:
        q = [val(DENSE, k, c, u[k]) - val(FLAT, k, c, u[k]) for c in range(n)]
        qd = [val(DENSE, jd, c, u[jd]) - val(FLAT, k, c, u[k]) for c in range(n)]

        def ahead(x: list[float]) -> bool:
            pm = [mean(x[i : i + 3]) for i in range(0, n, 3)]
            return mean(x) >= 0.005 and sum(1 for y in x if y > 0) >= 22 and sum(1 for y in pm if y > 0) >= 8

        def behind(x: list[float]) -> bool:
            pm = [mean(x[i : i + 3]) for i in range(0, n, 3)]
            return mean(x) <= -0.005 and sum(1 for y in x if y < 0) >= 22 and sum(1 for y in pm if y < 0) >= 8

        if ahead(q) and ahead(qd):
            return "M-AHEAD"
        if behind(q):
            return "D-AHEAD"
        if -0.005 < mean(q) < 0.005:
            return "LEVEL"
        return "UNDECIDED"

    del B
    classes = {k: cls(k) for k in range(0, k_max + 1)}
    if kstar is not None:
        cs = [classes[k] for k in range(kstar, k_max + 1)]
        if len(set(cs)) > 1:
            return "ORDERING NOT STABLE AFTER CONVERGENCE", kstar
        return {"M-AHEAD": "PERSISTS AT CONVERGENCE", "LEVEL": "LEVEL AT CONVERGENCE", "D-AHEAD": "DENSE AHEAD AT CONVERGENCE", "UNDECIDED": "LEAD NOT ESTABLISHED AT CONVERGENCE"}[cs[0]], kstar
    cd_, cm_ = conv[DENSE][k_max], conv[FLAT][k_max]
    if cd_ and not cm_ and classes[k_max] == "M-AHEAD":
        return "MEMORY AHEAD (DENSE CONVERGED, MEMORY STILL IMPROVING)", None
    if cm_ and not cd_ and classes[k_max] == "D-AHEAD":
        return "DENSE AHEAD (MEMORY CONVERGED, DENSE STILL IMPROVING)", None
    if not cd_ and cm_:
        return "CONVERGENCE NOT REACHED (DENSE STILL IMPROVING)", None
    if cd_ and not cm_:
        return "CONVERGENCE NOT REACHED (MEMORY STILL IMPROVING)", None
    return "CONVERGENCE NOT REACHED (BOTH STILL IMPROVING)", None


def baseline_(c: int) -> float:
    return synthetic.baseline(3 * (c // 3))


def random_spec(rng: random.Random, n: int) -> Spec:
    def arm(offset: float) -> ArmSpec:
        deltas = [rng.choice([0.0004, 0.0009, 0.002, 0.02, -0.01]) for _ in range(5)]
        g = gains(0.05 + offset, deltas)
        drun = {k: rng.choice([0.0004, 0.0009, 0.002, 0.02]) for k in range(5)}
        cell = {k: [rng.choice([0.0, 0.0, 0.004, -0.004, 0.012]) for _ in range(n)] for k in range(-1, 5)} if rng.random() < 0.5 else {}
        return ArmSpec(g, drun, cell)

    return Spec(arm(rng.choice([0.0, 0.01, -0.005])), arm(0.1), cells=n, p_used=lambda k, c: 0.08, x_mean=lambda k, c: 0.08)


@pytest.mark.parametrize("seed", range(40))
def test_analysis_matches_an_independent_oracle_on_random_registries(seed: int) -> None:
    rng = random.Random(core.test_seed(seed, CFG))
    n = 27
    spec = random_spec(rng, n)
    reg = synthetic.registry(CFG, spec)
    res = analysis.analyse(reg, synthetic.rate_table(K), CFG, k_max=K, bitwise=True, cells=n)
    if res["line_p"]["row"] in (1, 2):
        # a cause of section 12.2 (the dense gain or the baseline): only the rows above are the oracle's business
        assert res["line_p"]["row"] == 1 and 4 in res["line_p"]["cause_ids"]
        return
    want, kstar = oracle(reg, K, n)
    assert res["line_p"]["base_label"] == want and res["k_star"] == kstar


def test_scaled_denominators_never_used_for_a_registered_label() -> None:
    th = TH.scaled(12)
    assert (th.cells, th.parents, th.min_cells, th.min_parents) == (12, 4, 22, 8)



def test_x_mean_dense_is_reported_per_rung_and_changes_no_label() -> None:
    res = run(pair(SMALL, [0.02] * 5))
    for k in range(5):
        x = res["per_rung"][str(k)]["X_mean_dense"]
        assert x["n"] == 27 and abs(x["mean"] - 0.001) < 1e-12 and x["positive"] == 27  # the synthetic registry sets H_xmd = A + 0.001
    assert label_of(res) == "PERSISTS AT CONVERGENCE"
