# ruff: noqa: E501
"""P10IS1 label rules (ADR-0024 sections 8 and 9) on hand-built numbers whose answers are derived by hand in the comments, not by the helper under test: DEP (a, b, c with the qualification), matched compute (MC-A, MC-T,
MC-C), every row of the capacity step, the step and arm classes, the dense readings and their combination, dense at saturation, the saturation pair, the efficiency step and dense speed, and every outcome row.
Self-check only: not independent review, not Astra validation, not human approval."""

import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from studies.p10is1 import core, labels  # noqa: E402
from studies.p10is1.labels import McRead, Obs, Pt  # noqa: E402

TH = core.Thresholds.from_config()
GRID = TH.mc_grid


def S(i_map: dict[int, float], a_use: float = 0.9) -> dict[int, Pt]:
    return {u: Pt(i, a_use) for u, i in i_map.items()}


# --- DEP ---------------------------------------------------------------------------------------------------------------------------------
def test_dep_conditions_and_qualification() -> None:
    n = 2048  # G2 interval [34, 100] at 2,048 facts
    ok = Obs(n, correct=870, useful=800, disabled=64, shuffled=64, baseline=64)
    assert labels.dep_failures(ok, memory=True) == set()  # c - u = 70 is within the Binomial(1248, 100/2048) upper 1e-4 quantile
    assert labels.dep_failures(Obs(n, 870, 800, disabled=120, shuffled=64, baseline=64), memory=True) == {"a"}  # 120 > 100: memory disabled is not at chance
    assert labels.dep_failures(Obs(n, 870, 800, disabled=64, shuffled=300, baseline=64), memory=True) == {"b"}
    assert labels.dep_failures(Obs(n, 870, 800, disabled=64, shuffled=300, baseline=64), memory=False) == set()  # D-OQ: DEP-b is not defined for a map without a value table
    # c: excess 300 > quantile, and (300 - 1248 * 64 / 2048) / 2048 = 0.127 > 0.01
    assert labels.dep_failures(Obs(n, 1100, 800, disabled=64, shuffled=64, baseline=64), memory=True) == {"c"}
    # the same counts with c disqualified (R2 failed it at this fraction) fail nothing
    assert labels.dep_failures(Obs(n, 1100, 800, disabled=64, shuffled=64, baseline=64), memory=True, qualified={"a", "b"}) == set()
    # a_use below 0.25 (u = 400 of 2048 = 0.195): DEP does not apply
    assert labels.dep_failures(Obs(n, 1100, 400, disabled=500, shuffled=500, baseline=64), memory=True) == set()
    # a record without the count a condition needs fails (never passes)
    assert labels.dep_failures(Obs(n, 870, 800, disabled=None, shuffled=64, baseline=64), memory=True) == {"a"}
    assert labels.dep_failures(Obs(n, 870, 800, disabled=64, shuffled=64, baseline=None), memory=True) == {"c"}
    # ADR-0024 section 8.1: both parts; an excess that the backbone's own rate explains does not fail (baseline 200 of 2048: m b / n = 122)
    assert labels.dep_failures(Obs(n, 910, 800, disabled=64, shuffled=64, baseline=200), memory=True) == set()


def test_leakage_flag() -> None:
    assert not Obs(2048, 0, 0, unseen_n=64, unseen_correct=2).leakage and Obs(2048, 0, 0, unseen_n=2048, unseen_correct=900).leakage and not Obs(2048, 0, 0).leakage


# --- matched compute -----------------------------------------------------------------------------------------------------------------------
def test_mc_reading_capacity_mode() -> None:
    kw: dict[str, Any] = {"u_p": 8192, "run_first": 6 * 8192, "run_second": 6 * 8192, "grid": GRID, "mode": "capacity", "claim": "second"}
    r = labels.mc_reading(1.0, 1.6, **kw)  # the larger cell costs 1.6x: the smaller is read at the smallest grid value >= 1.6, that is 2.0
    assert r == McRead(labels.OK, 16384, 8192, 1.6)
    assert labels.mc_reading(1.0, 1.0, **kw) == McRead(labels.OK, 8192, 8192, 1.0)  # equal: both at U_P
    assert labels.mc_reading(1.0, 0.5, **kw) == McRead(labels.OK, 8192, 8192, 1.0)  # ruling 1: the larger cell costs no more, U_MC = U_P (never reads the larger later)
    assert labels.mc_reading(1.0, 1.25, **kw).first_update == 10240
    short = labels.mc_reading(1.0, 7.0, **kw)  # above the grid (6) -> MC-SHORT
    assert short.status == labels.MC_SHORT and short.first_update is None
    short2 = labels.mc_reading(1.0, 4.0, **{**kw, "run_first": 3 * 8192})  # the matched snapshot 4 x U_P is beyond the smaller cell's run length
    assert short2.status == labels.MC_SHORT


def test_mc_reading_dense_mode() -> None:
    kw: dict[str, Any] = {"u_p": 8192, "run_first": 6 * 8192, "run_second": 6 * 8192, "grid": GRID, "mode": "dense", "claim": "second"}
    # first = D-OQ, second = the arm. The arm costs 1.6x D-OQ: the arm at U_P, D-OQ at 2 x U_P
    assert labels.mc_reading(1.0, 1.6, **kw) == McRead(labels.OK, 16384, 8192, 1.6)
    # D-OQ costs 2x the arm (r = 0.5): D-OQ at U_P, the arm at 2 x U_P
    assert labels.mc_reading(2.0, 1.0, **kw) == McRead(labels.OK, 8192, 16384, 2.0)
    assert labels.mc_reading(1.0, 1.0, **kw) == McRead(labels.OK, 8192, 8192, 1.0)


def test_mc_combined_mc_c() -> None:
    kw: dict[str, Any] = {"u_p": 1000, "run_first": 6000, "run_second": 6000, "grid": GRID, "mode": "capacity"}
    # agree, both larger costlier: MC-A r = 1.2 (grid 1.25 -> 1,250), MC-T r = 1.6 (grid 2 -> 2,000): MC-C is the reading with the larger multiplier, MC-T's
    out = labels.mc_combined((1.0, 1.2), (1.0, 1.6), **kw)
    assert out["MC-A"].first_update == 1250 and out["MC-T"].first_update == 2000 and out["MC-C"] == out["MC-T"]
    # disagree: MC-A 1.2 (larger costlier), MC-T 0.5 (smaller costlier): MC-AMBIGUOUS, M = max(1.2, 1/1.2, 0.5, 2) = 2 -> the larger cell at U_P, the smaller at 2 x U_P
    amb = labels.mc_combined((1.0, 1.2), (1.0, 0.5), **kw)["MC-C"]
    assert amb is not None and amb.ambiguous and amb.first_update == 2000 and amb.second_update == 1000 and amb.status == labels.OK
    # disagree and the matched snapshot beyond the smaller cell's run: MC-SHORT
    assert labels.mc_combined((1.0, 1.2), (1.0, 0.1), **kw)["MC-C"].status == labels.MC_SHORT  # type: ignore[union-attr]
    # an exactly equal measure agrees with the other: MC-A equal, MC-T 1.6 -> MC-C is MC-T's
    eq = labels.mc_combined((1.0, 1.0), (1.0, 1.6), **kw)
    assert eq["MC-C"] == eq["MC-T"] and eq["MC-C"].first_update == 2000  # type: ignore[union-attr]
    # both equal: both at U_P
    assert labels.mc_combined((1.0, 1.0), (1.0, 1.0), **kw)["MC-C"] == McRead(labels.OK, 1000, 1000, 1.0)
    # MC-T not measured: MC-T and MC-C are absent
    only_a = labels.mc_combined((1.0, 1.2), None, **kw)
    assert only_a["MC-T"] is None and only_a["MC-C"] is None and only_a["MC-A"] is not None
    # dense mode ambiguity: the arm (second) at U_P and D-OQ (first) at the later snapshot
    d = labels.mc_combined((1.0, 1.2), (1.0, 0.5), **{**kw, "mode": "dense"})["MC-C"]
    assert d is not None and d.first_update == 2000 and d.second_update == 1000


# --- the capacity step, every row ------------------------------------------------------------------------------------------------------------
U_P, RUN = 8, 48
SMALL_BASE = {8: 0.5, 10: 0.6, 12: 0.7, 16: 0.9, 20: 1.0, 24: 1.1, 32: 1.2, 48: 1.3}
LARGE_BASE = {8: 2.5, 10: 2.6, 12: 2.7, 16: 2.8, 20: 2.9, 24: 3.0, 32: 3.0, 48: 3.0}
MC_OK = {"MC-A": McRead(labels.OK, 10, 8, 1.25), "MC-T": McRead(labels.OK, 12, 8, 1.5), "MC-C": McRead(labels.OK, 12, 8, 1.5)}


def ctx(**kw: Any) -> labels.StepCtx:
    base: dict[str, Any] = {
        "u_p": U_P, "run_small": RUN, "run_large": RUN, "ref_ok": True, "leakage": False, "dep_failed_small": frozenset(), "dep_failed_large": frozenset(), "small_full": True, "large_full": True,
        "small_loaded": True, "mc": MC_OK,
    }  # fmt: skip
    base.update(kw)
    return labels.StepCtx(**base)


def verdict(small: dict[int, float] | None = None, large: dict[int, Any] | None = None, **kw: Any) -> str:
    return labels.capacity_panel(S(small or SMALL_BASE), {u: (p if isinstance(p, Pt) else Pt(p, 0.9)) for u, p in (large or LARGE_BASE).items()}, ctx(**kw), TH).verdict


def test_capacity_panel_every_row() -> None:
    # CAPACITY: d_MU = 2.5 - 0.5 = 2.0; d_MC = 2.5 - 0.6 (MC-A), 2.5 - 0.7 (MC-T, MC-C); d_SAT = 2.5 - 1.3 = 1.2; plateau gain of the smaller 1.3 - 1.1 = 0.2, so 1.2 - 0.4 = 0.8 >= 0.5; a_use 0.9
    assert verdict() == labels.CAPACITY
    # row 1
    assert verdict(ref_ok=False) == labels.NOT_EVALUATED and verdict(leakage=True) == labels.NOT_EVALUATED
    # row 2 beats rows 3 to 10, in either cell
    assert verdict(dep_failed_small=frozenset({12})) == labels.DEPENDENCE_FAILED and verdict(dep_failed_large=frozenset({48})) == labels.DEPENDENCE_FAILED
    # row 3: i(N; U_P) >= 4.5
    assert verdict(small={**SMALL_BASE, 8: 4.6}) == labels.CEILING
    # row 4 broken one condition at a time falls to row 5 (the gain at matched updates is still 0.5 or more)
    assert verdict(mc={**MC_OK, "MC-T": McRead(labels.MC_SHORT, None, 8, 9.0)}) == labels.GAIN_ONLY  # a pair MC-SHORT in MC-T fails the condition
    assert verdict(mc={**MC_OK, "MC-C": McRead(labels.MC_SHORT, None, 8, 9.0)}) == labels.GAIN_ONLY  # and MC-SHORT in MC-C fails it too (ruling 6)
    assert verdict(mc={"MC-A": MC_OK["MC-A"], "MC-T": None, "MC-C": None}) == labels.CAPACITY  # MC-T not measured: MC-A alone decides (the report adds MATCHED COMPUTE IN MC-A ONLY)
    assert verdict(mc={"MC-A": McRead(labels.MC_SHORT, None, 8, 9.0), "MC-T": None, "MC-C": None}) == labels.GAIN_ONLY
    small_late = {**SMALL_BASE, 12: 2.2}  # MC-T and MC-C read the smaller cell at 12: d_MC = 2.5 - 2.2 = 0.3 < 0.5 (MC-A at 10 is 1.9)
    assert verdict(small=small_late) == labels.GAIN_ONLY
    small_a = {**SMALL_BASE, 10: 2.2}  # only MC-A reads 10
    assert verdict(small=small_a) == labels.GAIN_ONLY
    assert verdict(small_loaded=False) == labels.GAIN_ONLY
    assert verdict(large={**LARGE_BASE, 8: Pt(2.5, 0.49)}) == labels.GAIN_ONLY  # a_use(4N; U_P) < 0.5
    assert verdict(large={**LARGE_BASE, 8: 1.7}, mc={"MC-A": McRead(labels.OK, 8, 8, 1.0), "MC-T": McRead(labels.OK, 8, 8, 1.0), "MC-C": McRead(labels.OK, 8, 8, 1.0)}) == labels.GAIN_ONLY  # d_MU = 1.2, d_SAT = 1.7 - 1.3 = 0.4 < 0.5
    small_gain = {**SMALL_BASE, 20: 0.9, 24: 0.9}  # last-doubling gain 1.3 - 0.9 = 0.4: 1.2 - 0.8 = 0.4 < 0.5
    assert verdict(small=small_gain) == labels.GAIN_ONLY
    # rows 6 and 7
    small_hi = {8: 2.0, 10: 2.1, 12: 2.2, 16: 2.3, 20: 2.4, 24: 2.5, 32: 2.5, 48: 2.5}
    large_lo = {8: 1.0, 10: 1.0, 12: 1.0, 16: 1.1, 20: 1.1, 24: 1.2, 32: 1.2, 48: 1.2}  # d_MU = -1.0, d_FULL = 1.2 - 2.5 = -1.3
    assert verdict(small=small_hi, large=large_lo) == labels.REVERSED
    large_mid = {**large_lo, 48: 2.2}  # d_FULL = 2.2 - 2.5 = -0.3 > -0.5 and d_MU = -1.0
    assert verdict(small=small_hi, large=large_mid) == labels.BEHIND
    # rows 8 and 9: |d_MU| = 0.1, |d_FULL| = 0.1, both cells full
    small_n = {8: 2.0, 10: 2.0, 12: 2.0, 16: 2.0, 20: 2.0, 24: 2.0, 32: 2.0, 48: 2.0}
    large_n = {8: 2.1, 10: 2.1, 12: 2.1, 16: 2.1, 20: 2.1, 24: 2.1, 32: 2.1, 48: 2.1}
    assert verdict(small=small_n, large=large_n) == labels.NULL
    assert verdict(small=small_n, large=large_n, small_loaded=False) == labels.FLAT_NOT_LOADED
    assert verdict(small=small_n, large=large_n, small_full=False, small_loaded=False) == labels.UNRESOLVED  # a cell that is not full cannot be NULL or FLAT
    assert verdict(small=small_n, large=large_n, large_full=False) == labels.UNRESOLVED
    # row 10: |d_MU| = 0.3 is between 0.25 and 0.5
    large_u = {u: 2.3 for u in small_n}
    assert verdict(small=small_n, large=large_u) == labels.UNRESOLVED


def test_capacity_replicate_and_classes() -> None:
    r = labels.capacity_replicate({"A": labels.StepResult(labels.CAPACITY, {}), "B": labels.StepResult(labels.CAPACITY, {})})
    assert r.verdict == labels.CAPACITY
    r2 = labels.capacity_replicate({"A": labels.StepResult(labels.CAPACITY, {}), "B": labels.StepResult(labels.GAIN_ONLY, {})})
    assert r2.verdict == labels.PANEL_DISAGREE
    no = [False] * 5
    cls = lambda v, nf=no: labels.capacity_step_class(v, nf, TH)  # noqa: E731
    C, G, N, R, X, F, D, P, B = labels.CAPACITY, labels.GAIN_ONLY, labels.NULL, labels.REVERSED, labels.NOT_EVALUATED, labels.FLAT_NOT_LOADED, labels.DEPENDENCE_FAILED, labels.PANEL_DISAGREE, labels.CEILING
    assert cls([X, X, C, C, C]) == X and cls([X, C, C, C, C]) == labels.MIXED
    assert cls([D, D, C, C, C]) == D and cls([X, X, D, D, C]) == X  # first match: NOT_EVALUATED before DEPENDENCE_FAILED
    assert cls([P, P, C, C, C]) == labels.NOT_REPLICATED
    assert cls([C] * 5) == labels.CAPACITY_STEP and cls([C, C, G, G, C]) == labels.GAIN_STEP and cls([C, C, G, G, N]) != labels.GAIN_STEP
    assert cls([B, B, F, F, C]) == labels.NOT_LOADED and cls([B, F, F, C, C]) != labels.NOT_LOADED
    assert cls([R, R, R, R, C]) == labels.REVERSED and cls([N, N, R, R, C]) == labels.NO_GAIN and cls([N, N, N, C, C]) == labels.MIXED
    assert cls([N, C, G, C, C], [True, True, False, False, False]) == labels.NOT_FULL_WITHIN_BUDGET  # the smaller cell not full in 2 of 5, nothing earlier matches
    assert cls([N, C, G, C, C], [True, False, False, False, False]) == labels.MIXED
    with pytest.raises(ValueError):
        labels.capacity_step_class([C] * 4, no, TH)
    trans = {"1K→4K": ["C1", "N1"], "4K→16K": ["C2", "N2"]}
    arm = lambda c1, n1, c2, n2, a=True: labels.capacity_arm_class({"C1": c1, "N1": n1, "C2": c2, "N2": n2}, trans, a)  # noqa: E731
    CS, NL, NF, NG, RV, MX = labels.CAPACITY_STEP, labels.NOT_LOADED, labels.NOT_FULL_WITHIN_BUDGET, labels.NO_GAIN, labels.REVERSED, labels.MIXED
    assert arm(CS, NL, CS, NL) == labels.CAPACITY_SUPPORTED and arm(CS, NL, CS, NL, False) == labels.CAPACITY_ONE_TRANSITION
    assert arm(CS, NL, CS, RV) == labels.CAPACITY_ONE_TRANSITION  # a REVERSED step blocks SUPPORTED
    assert arm(X, X, CS, NL) == X and arm(X, NL, CS, NL) == labels.CAPACITY_ONE_TRANSITION  # only a transition whose every step is NOT_EVALUATED gives NOT_EVALUATED
    assert arm(D, NL, CS, NL) == D
    assert arm(NL, NF, NG, MX) == labels.NOT_TESTED_BY_LOAD  # in the first transition every step is NOT LOADED or NOT FULL WITHIN BUDGET
    assert arm(NG, MX, NG, RV) == labels.CAPACITY_NOT_SUPPORTED and arm(NG, MX, MX, MX) == labels.INTERMEDIATE


# --- the dense comparison ------------------------------------------------------------------------------------------------------------------------
def rep(mu: float = 0.5, a: float = 0.5, t: float = 0.5, c: float = 0.5, best: float = 0.5, **over: Any) -> labels.DenseRep:
    d = {"MU": {"A": mu, "B": mu}, "MC-A": {"A": a, "B": a}, "MC-T": {"A": t, "B": t}, "MC-C": {"A": c, "B": c}, "D-BEST": {"A": best, "B": best}}
    status = dict.fromkeys(labels.READINGS, labels.OK)
    blocked = dict.fromkeys(labels.READINGS, False)
    for k, v in over.items():
        if k == "status":
            status.update(v)
        elif k == "blocked":
            blocked.update(v)
        elif k == "panel_b":
            d = {r: {"A": d[r]["A"], "B": v.get(r, d[r]["B"])} for r in d}
    return labels.DenseRep(d, status, blocked)


def test_dense_cell_labels() -> None:
    L = lambda reps, mct=True: labels.dense_cell_label(reps, TH, mct_measured=mct)  # noqa: E731
    five = [rep() for _ in range(5)]
    assert L(five)["label"] == labels.STORE_NOT_BEHIND
    # DENSE AHEAD: d <= -0.25 on either panel in >= 4 replicates in one reading; at matched updates only -> annotated
    mu_only = [rep(mu=-0.3) for _ in range(4)] + [rep()]
    assert L(mu_only)["label"] == labels.DENSE_AHEAD_NOT_MC and L(mu_only)["counts"]["MU"] == 4
    best_only = [rep(best=-0.9) for _ in range(5)]
    assert L(best_only)["label"] == labels.DENSE_AHEAD_NOT_MC  # D-BEST alone: no matched-compute reading
    assert L([rep(a=-0.26) for _ in range(4)] + [rep()])["label"] == labels.DENSE_AHEAD  # a matched-compute reading
    assert L([rep(t=-0.25) for _ in range(5)])["label"] == labels.DENSE_AHEAD  # exactly -0.25 counts (<=)
    assert L([rep(c=-0.4) for _ in range(4)] + [rep()])["label"] == labels.DENSE_AHEAD  # MC-C counts as a matched-compute reading
    assert L([rep(mu=-0.3) for _ in range(3)] + [rep(), rep()])["label"] == labels.DENSE_SPLIT_CELL  # only 3 of 5
    # either panel counts for a dense lead
    assert L([rep(panel_b={"MU": -0.5}) for _ in range(4)] + [rep()])["label"] == labels.DENSE_AHEAD_NOT_MC
    # MC-SHORT replicates do not count in that reading
    shorts = [rep(a=-0.5, status={"MC-A": labels.MC_SHORT}) for _ in range(4)] + [rep()]
    assert L(shorts)["counts"]["MC-A"] == 0 and L(shorts)["label"] == labels.DENSE_SPLIT_CELL  # not clear either: MC-SHORT blocks STORE NOT BEHIND
    # STORE NOT BEHIND needs d > -0.25 on both panels in all 5 replicates in every reading
    assert L([rep()] * 4 + [rep(panel_b={"MC-T": -0.2499})])["label"] == labels.STORE_NOT_BEHIND
    assert L([rep()] * 4 + [rep(panel_b={"D-BEST": -0.25})])["label"] == labels.DENSE_SPLIT_CELL  # exactly -0.25 is not clear of it
    assert L(five, mct=False)["label"] == labels.DENSE_SPLIT_CELL  # MC-T not measured: never STORE NOT BEHIND
    assert L(five[:4])["label"] == labels.DENSE_SPLIT_CELL
    # D-OQ DEP blocked at a reading: a store-favouring label is not established, a dense lead still stands
    assert L([rep()] * 4 + [rep(blocked={"MU": True})])["label"] == labels.DENSE_SPLIT_CELL
    assert L([rep(mu=-0.3, blocked={"MU": True}) for _ in range(4)] + [rep()])["label"] == labels.DENSE_AHEAD_NOT_MC


def test_dense_arm_combination_and_saturation() -> None:
    A = lambda cells, sat: labels.dense_arm_label(cells, sat, TH)  # noqa: E731
    NB, DA, DAN, SP = labels.STORE_NOT_BEHIND, labels.DENSE_AHEAD, labels.DENSE_AHEAD_NOT_MC, labels.DENSE_SPLIT_CELL
    assert A({}, {"8K/1K": labels.DENSE_HOLDS_MORE}) == labels.ARM_NOT_APPLICABLE  # no CAPACITY STEP: not applicable even when the dense map holds more
    assert A({"8K/4K": NB, "32K/16K": NB}, {"8K/1K": labels.SAME_AT_SATURATION, "32K/4K": labels.STORE_HOLDS_MORE}) == labels.ARM_NOT_BEHIND
    assert A({"8K/4K": NB, "32K/16K": DAN}, {}) == labels.ARM_DENSE_AHEAD  # any such cell
    assert A({"8K/4K": DA}, {}) == labels.ARM_DENSE_AHEAD
    assert A({"8K/4K": NB}, {"8K/1K": labels.DENSE_HOLDS_MORE}) == labels.ARM_DENSE_AHEAD  # any loaded cell
    assert A({"8K/4K": NB, "32K/16K": SP}, {}) == labels.ARM_DENSE_SPLIT
    # dense at saturation
    def sat(d: float = 0.0, ratio: float | None = 1.2, full: bool = True, cost: bool = True, blocked: bool = False) -> labels.SatDenseRep:
        return labels.SatDenseRep({"A": d, "B": d}, {"A": ratio, "B": ratio}, full, cost, blocked)

    S_ = lambda reps, mct=True: labels.dense_at_saturation(reps, TH, mct_measured=mct)  # noqa: E731
    assert S_([sat(-0.25) for _ in range(4)] + [sat()])["label"] == labels.DENSE_HOLDS_MORE
    assert S_([sat(-0.24) for _ in range(5)])["label"] == labels.STORE_HOLDS_MORE
    assert S_([sat(ratio=1.09)] + [sat()] * 4)["label"] == labels.SAME_AT_SATURATION
    assert S_([sat(ratio=None)] * 5)["label"] == labels.STORE_HOLDS_MORE  # a zero denominator counts as at least 1.10
    assert S_([sat(full=False)] + [sat()] * 4)["sublabels"] == [labels.DENSE_STILL_RISING]
    assert S_([sat()] * 5, mct=False)["label"] == labels.SAME_AT_SATURATION  # the cost condition needs MC-T
    assert S_([sat(cost=False)] + [sat()] * 4)["label"] == labels.SAME_AT_SATURATION
    assert S_([sat(blocked=True)] + [sat()] * 4)["label"] == labels.SAME_AT_SATURATION
    assert S_([sat()] * 4)["label"] == labels.SAME_AT_SATURATION  # fewer than five replicates


# --- the saturation pair -------------------------------------------------------------------------------------------------------------------
def test_saturation_pair_and_outcome() -> None:
    from studies.p10s1 import classes as c1

    def side(facts: int, slots: int, i_final: float, *, loaded: bool = True, dep: bool = False) -> dict[str, Any]:
        ser = S({16: i_final - 0.05, 32: i_final})
        return {"facts": facts, "slots": slots, "series": {"A": ser, "B": ser}, "length": 32, "loaded": loaded, "dep_failed": dep}

    small = side(2048, 256, 2.0)  # S = 2048 x 2.0 = 4096 bits
    large = side(8192, 1024, 2.0)  # S = 8192 x 2.0 = 16384: rho = 4.0 >= 3.0
    assert labels.saturation_pair(small, large, ref_ok=True, leakage=False, th=TH).verdict == c1.PROPORTIONAL
    sub = labels.saturation_pair(small, side(8192, 1024, 1.4), ref_ok=True, leakage=False, th=TH)  # rho = 8192 x 1.4 / 4096 = 2.8 < 3
    assert sub.verdict == c1.SUBPROPORTIONAL and abs(sub.detail["rho"]["A"] - 2.8) < 1e-9
    assert labels.saturation_pair(small, large, ref_ok=False, leakage=False, th=TH).verdict == c1.NOT_EVALUATED
    assert labels.saturation_pair(small, side(8192, 1024, 2.0, dep=True), ref_ok=True, leakage=False, th=TH).verdict == c1.DEPENDENCE_FAILED
    assert labels.saturation_pair(small, side(8192, 1024, 2.0, loaded=False), ref_ok=True, leakage=False, th=TH).verdict == c1.NOT_FULL
    assert sub.detail["small"]["b_bits_per_slot"]["A"] == 2048 * 2.0 / 256  # b(N) = S(N) / N
    o = labels.saturation_outcome({"F-OQ": c1.SAT_PROPORTIONAL_ALL_PAIRS, "T-OQ": c1.SAT_DOES_NOT_SCALE, "H8": c1.SAT_PROPORTIONAL_ALL_PAIRS}, sat256_absent=False)
    assert o["label"] == labels.SAT_PROPORTIONAL and o["arms"] == ["F-OQ"]
    assert labels.saturation_outcome({"H8": c1.SAT_PROPORTIONAL_ALL_PAIRS, "F-OQ": c1.INTERMEDIATE, "T-OQ": c1.INTERMEDIATE}, sat256_absent=False)["label"] == labels.SAT_INCONCLUSIVE  # H8 alone cannot give PROPORTIONAL
    assert labels.saturation_outcome({"F-OQ": c1.SAT_DOES_NOT_SCALE, "T-OQ": c1.SAT_DOES_NOT_SCALE}, sat256_absent=True)["label"] == labels.SAT_SUBPROPORTIONAL
    assert labels.saturation_outcome({"F-OQ": c1.SAT_NOT_MEASURED, "T-OQ": c1.SAT_NOT_MEASURED}, sat256_absent=False)["label"] == labels.SAT_NOT_MEASURED_OUTCOME
    inc = labels.saturation_outcome({"F-OQ": c1.DEPENDENCE_FAILED, "T-OQ": c1.SAT_NOT_MEASURED}, sat256_absent=False)
    assert inc["label"] == labels.SAT_INCONCLUSIVE and "DEPENDENCE_FAILED" in inc["reasons"]


# --- efficiency -------------------------------------------------------------------------------------------------------------------------------
def test_efficiency_pieces() -> None:
    from studies.p10s1 import classes as c1

    ser = lambda m: S(m)  # noqa: E731
    both = {"A": ser({1000: 1.0, 2000: 2.0, 4000: 3.5, 8000: 3.6}), "B": ser({1000: 1.0, 2000: 2.0, 4000: 3.5, 8000: 3.6})}
    r = labels.u_t_of(both, 8000, {})
    assert r.s_hit == 4000 and r.s_prev == 2000 and not r.dep_failed and r.ut.kind == "exact"
    # interpolation of the minimum of the two panels' i against log2(updates): 2.0 -> 3.5 over 2000 -> 4000, 3.0 at 2/3 of the way (1.0 / 1.5)
    assert abs(r.ut.lo - 2000 * 2 ** (1.0 / 1.5)) < 1e-6
    failed = labels.u_t_of(both, 8000, {"A": frozenset({4000})})
    assert failed.dep_failed
    never = labels.u_t_of({"A": ser({1000: 1.0, 2000: 2.0}), "B": ser({1000: 1.0, 2000: 2.0})}, 2000, {})
    assert never.ut.kind == "right"
    # dense speed per reading: arm exact u_T 1000, cost 1.0; D-OQ exact u_T 100, cost 2.0 -> c_T(dense) = 200 <= 0.8 x 1000
    ut = lambda v: c1.UT("exact", v, v)  # noqa: E731
    arm_ut = [[ut(1000.0), ut(1000.0)] for _ in range(5)]
    fast = [[ut(100.0), ut(100.0)] for _ in range(5)]
    slow = [[ut(900.0), ut(900.0)] for _ in range(5)]
    assert labels.dense_speed(arm_ut, fast, 1.0, 2.0, TH) == labels.DENSE_FASTER
    assert labels.dense_speed(arm_ut, slow, 1.0, 2.0, TH) == labels.DENSE_NOT_FASTER  # c_T(dense) = 1800 > 800 in all 5 on both panels
    mixed = [fast[0], fast[1], fast[2], slow[0], slow[1]]
    assert labels.dense_speed(arm_ut, mixed, 1.0, 2.0, TH) == labels.DENSE_SPEED_UNDECIDED  # 3 of 5 sure, not above in all 5
    four = [fast[0], fast[1], fast[2], fast[3], slow[0]]
    assert labels.dense_speed(arm_ut, four, 1.0, 2.0, TH) == labels.DENSE_FASTER
    one_panel = [[ut(100.0), ut(900.0)] for _ in range(5)]
    assert labels.dense_speed(arm_ut, one_panel, 1.0, 2.0, TH) == labels.DENSE_FASTER  # a replicate counts if either panel satisfies it
    assert labels.dense_speed(arm_ut, slow, 1.0, 2.0, TH, blocked=[True, False, False, False, False]) == labels.DENSE_SPEED_UNDECIDED  # a D-OQ DEP block does not establish NOT FASTER
    cens = [[c1.UT("right", 8000.0, float("inf")), c1.UT("right", 8000.0, float("inf"))] for _ in range(5)]
    assert labels.dense_speed(cens, cens, 1.0, 2.0, TH) == labels.DENSE_SPEED_UNDECIDED  # both above the run: the bounds do not say
    assert labels.dense_speed(arm_ut, cens, 1.0, 2.0, TH) == labels.DENSE_NOT_FASTER  # D-OQ above 8,000 updates against the arm's 1,000: not faster for every value the bound allows


def test_efficiency_outcome_rows() -> None:
    SUP, NS, INT = "EFFICIENCY_SUPPORTED", "EFFICIENCY_NOT_SUPPORTED", labels.INTERMEDIATE
    NF, F, U = labels.DENSE_NOT_FASTER, labels.DENSE_FASTER, labels.DENSE_SPEED_UNDECIDED

    def run(a: dict[str, str], t: dict[str, str] | None, da: dict[str, list[str]], dt: dict[str, list[str]] | None = None) -> dict[str, Any]:
        cls = {"E-A": a, **({"E-T": t} if t is not None else {})}
        dense = {"E-A": da, **({"E-T": dt or {}} if t is not None else {})}
        return labels.efficiency_outcome(cls, dense, mct_measured=t is not None)

    sup = {"F-OQ": SUP, "T-OQ": INT}
    assert run(sup, sup, {"F-OQ": [NF, NF]}, {"F-OQ": [NF]})["label"] == labels.EFFICIENCY_POSITIVE
    assert run(sup, sup, {"F-OQ": [NF, F]}, {"F-OQ": [NF]})["label"] == labels.EFFICIENCY_NEGATIVE  # row 4 second clause: D-OQ faster at one cell in one reading
    assert run(sup, sup, {"F-OQ": [NF, U]}, {"F-OQ": [NF]})["label"] == labels.EFFICIENCY_INCONCLUSIVE and "DENSE SPEED UNDECIDED" in run(sup, sup, {"F-OQ": [NF, U]}, {"F-OQ": [NF]})["reasons"]
    only_a = {"F-OQ": SUP, "T-OQ": INT}
    assert run(only_a, {"F-OQ": INT, "T-OQ": INT}, {"F-OQ": [NF]}, {})["label"] == labels.EFFICIENCY_INCONCLUSIVE  # supported in E-A only: no positive; READINGS DISAGREE
    assert "READINGS DISAGREE" in run(only_a, {"F-OQ": INT, "T-OQ": INT}, {"F-OQ": [NF]}, {})["reasons"]
    ns = {"F-OQ": NS, "T-OQ": NS}
    assert run(ns, None, {})["label"] == labels.EFFICIENCY_NEGATIVE and run(ns, None, {})["e_a_only"]  # (E-A ONLY; MEASURED COST NOT AVAILABLE)
    assert run({"F-OQ": INT, "T-OQ": INT}, ns, {}, {})["label"] == labels.EFFICIENCY_NEGATIVE  # both in E-T alone
    nm = run(sup, None, {"F-OQ": [NF, NF]})
    assert nm["label"] == labels.EFFICIENCY_INCONCLUSIVE and "MEASURED COST NOT AVAILABLE" in nm["reasons"]  # the positive is unreachable without E-T


# --- the capacity outcome and the rest --------------------------------------------------------------------------------------------------------
def test_capacity_outcome_rows() -> None:
    SUP, NSUP, INT = labels.CAPACITY_SUPPORTED, labels.CAPACITY_NOT_SUPPORTED, labels.INTERMEDIATE
    NB, DA, SP, NA = labels.ARM_NOT_BEHIND, labels.ARM_DENSE_AHEAD, labels.ARM_DENSE_SPLIT, labels.ARM_NOT_APPLICABLE

    def arms(foq: tuple[str, str], toq: tuple[str, str], ivf: tuple[str, str]) -> dict[str, labels.ArmCapacity]:
        return {a: labels.ArmCapacity(a, *v) for a, v in (("F-OQ", foq), ("T-OQ", toq), ("F-OQ-IVF", ivf))}

    out = lambda a, nf=False, mct=True: labels.capacity_outcome(a, every_step_unloaded_or_unfull=nf, mct_measured=mct)  # noqa: E731
    p = out(arms((SUP, NB), (INT, NA), (INT, NA)))
    assert p["label"] == labels.CAPACITY_POSITIVE and p["row"] == 3 and not p["post_hoc_only"]
    ph = out(arms((INT, NA), (INT, NA), (SUP, NB)))
    assert ph["label"] == labels.CAPACITY_POSITIVE and ph["post_hoc_only"]  # a positive carried by F-OQ-IVF alone
    both = out(arms((SUP, NB), (INT, NA), (SUP, NB)))
    assert not both["post_hoc_only"]
    assert out(arms((SUP, NB), (SUP, DA), (INT, NA)))["label"] == labels.CAPACITY_POSITIVE  # row 3 is first: one supported arm NOT BEHIND is enough
    na = out(arms((NSUP, NA), (NSUP, NA), (INT, NA)))
    assert na["label"] == labels.CAPACITY_NEGATIVE and na["clause"] == "(a)"
    nb = out(arms((SUP, DA), (INT, NA), (SUP, DA)))
    assert nb["label"] == labels.CAPACITY_NEGATIVE and nb["clause"] == "(b)"
    assert out(arms((SUP, DA), (SUP, SP), (INT, NA)))["label"] == labels.CAPACITY_INCONCLUSIVE  # not every supported arm is DENSE AHEAD
    assert out(arms((INT, NA), (INT, NA), (INT, NA)))["label"] == labels.CAPACITY_INCONCLUSIVE  # an empty set never satisfies (b)
    assert out(arms((INT, NA), (INT, NA), (INT, NA)), nf=True)["label"] == labels.CAPACITY_NOT_TESTED
    assert out(arms((SUP, DA), (INT, NA), (INT, NA)), nf=True)["label"] == labels.CAPACITY_NEGATIVE  # negatives come before NOT TESTED
    assert out(arms((SUP, NB), (INT, NA), (INT, NA)), mct=False)["mct_note"] == labels.MEASURED_COST_NOT_AVAILABLE


def test_sparse_label_and_h8() -> None:
    def reps(v: float, n: int = 5, cells: tuple[str, ...] = ("8K/4K", "32K/16K")) -> list[dict[str, dict[str, float]]]:
        return [{c: {"A": v, "B": v} for c in cells} for _ in range(n)]

    assert labels.sparse_label(reps(1.03), TH) == labels.TREE_AHEAD and labels.sparse_label(reps(1.0299), TH) == labels.TREE_COMPETITIVE
    assert labels.sparse_label(reps(0.97), TH) == labels.TREE_COMPETITIVE and labels.sparse_label(reps(0.9699), TH) == labels.TREE_BEHIND
    four = reps(1.05, 4) + reps(0.5, 1)
    assert labels.sparse_label(four, TH) == labels.TREE_AHEAD  # >= 4 of 5 at both cells
    one_panel = [{c: {"A": 1.1, "B": 0.5} for c in ("8K/4K", "32K/16K")} for _ in range(5)]
    assert labels.sparse_label(one_panel, TH) == labels.TREE_BEHIND  # a favouring label needs both panels
    assert labels.key_learning_limited(labels.CAPACITY_SUPPORTED, labels.INTERMEDIATE) and not labels.key_learning_limited(labels.CAPACITY_SUPPORTED, labels.CAPACITY_SUPPORTED)
    ann = labels.h8_annotations(["8K/4K"], ["2K/4K", "8K/4K"], ["2K/1K", "2K/4K", "8K/4K"])
    assert ann == {"2K/1K": "H8 NOT CALIBRATED AT U_P AT 2K/1K", "8K/4K": labels.UNDERTRAINED}


def test_tags() -> None:
    t = labels.tagged(labels.CAPACITY_POSITIVE, "x")
    assert core.STANDING_TAG in t and labels.emit(t) == t
    with pytest.raises(ValueError):
        labels.emit("CAPACITY-POSITIVE without the tag")
    with pytest.raises(ValueError):
        labels.emit("the arm is CAPACITY_SUPPORTED and NOT BEHIND DENSE")
    assert labels.emit("DENSE AHEAD and CAPACITY-NEGATIVE need no tag") and not labels.is_positive("DENSE NOT FASTER")
    assert labels.printable(labels.CAPACITY_INCONCLUSIVE) == labels.CAPACITY_INCONCLUSIVE and core.STANDING_TAG in labels.printable(labels.STORE_NOT_BEHIND)
