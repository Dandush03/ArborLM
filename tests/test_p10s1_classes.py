# ruff: noqa: E501
"""P10S1 verdicts, classes, labels and outcomes (ADR-0021 section 8) on constructed counts: every row of the capacity step verdict, the step and arm classes (enumerated), the dense
labels, the outcomes (an unevaluated or untested study is never a negative), the efficiency line with every censoring case checked against a brute-force reading of 'holds for every
value the bounds allow', matched compute, and the STORE ONLY; ORACLE-ADDRESSED tag on every positive label. Unit-test seeds only (921001-921999); no model, no data. Self-check only:
not independent review, not Astra validation, not human approval."""

import itertools
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from studies.p10s1 import classes as C  # noqa: E402
from studies.p10s1 import core  # noqa: E402

N = 8192
U_P = core.U_P
RUN_SMALL, RUN_LARGE = 6 * U_P, 4 * U_P


def obs(a: float, n: int = N, *, chance_disabled: bool = True, unseen: int = 64) -> C.PanelObs:
    useful = int(round(a * n))
    chance = int(round(n / 32))
    return C.PanelObs(n, useful, useful, chance if chance_disabled else n // 2, chance, chance, 2048, unseen)


def view(profile, run: int, u_p: int = U_P, extra: tuple[int, ...] = (), **kw) -> C.View:
    """A view whose a_use at update u is ``profile(u)``."""
    return C.View({u: obs(profile(u), **kw) for u in core.snapshot_updates(u_p, run, extra)}, run, u_p)


def sat(a_max: float, tau: float = 1500.0):
    return lambda u: a_max * (1.0 - math.exp(-u / tau))


MC_OK = C.McEntry("OK", 3 * U_P, U_P, 3.0, "small")
MC_SHORT = C.McEntry(C.MC_SHORT, None, None, 7.0, None)


def small_view(profile) -> C.View:
    return view(profile, RUN_SMALL, extra=(3 * U_P,))


def large_view(profile) -> C.View:
    return view(profile, RUN_LARGE)


def verdict(small: C.View, large: C.View, mc: C.McEntry = MC_OK, *, ref_ok: bool = True, leakage: bool = False) -> str:
    return C.capacity_panel(small, large, mc, ref_ok=ref_ok, leakage=leakage).verdict


# --- information of a count --------------------------------------------------------------------------------------------------------------
def test_i_of_a_use_matches_the_adr_checkpoints() -> None:
    for a, i in ((0.5, 1.523), (0.8, 3.287), (0.9, 4.036), (0.95, 4.466)):
        assert core.bits_per_fact(int(round(a * N)), N) == pytest.approx(i, abs=0.01)
    assert core.bits_per_fact(int(N / 32), N) == 0.0  # chance
    assert core.bits_per_fact(core.chance_interval(N).high, N) == 0.0 and core.bits_per_fact(core.chance_interval(N).high + 1, N) > 0.0
    assert [core.chance_interval(n)[2:4] for n in (2048, 8192, 32768)] == [(34, 100), (192, 325), (894, 1159)]
    assert core.i_to_a_use(4.0) == pytest.approx(0.896, abs=0.002)


def test_dep_gate() -> None:
    assert obs(0.9).dep() is True
    assert obs(0.1).dep() is None  # a_use below 0.25: DEP does not apply
    assert obs(0.9, chance_disabled=False).dep() is False  # memory disabled does not give chance
    assert C.PanelObs(N, 7800, 7000, 256, 256, 256, 2048, 64).dep() is False  # a_use < 0.95 x raw accuracy
    assert C.PanelObs(N, 7000, 7000, 256, 1500, 256, 2048, 64).dep() is False  # value shuffle does not give chance
    assert obs(0.9, unseen=300).leakage and not obs(0.9).leakage


# --- capacity: every row of the step verdict ----------------------------------------------------------------------------------------------
def test_row1_not_evaluated() -> None:
    s, g = small_view(sat(0.35)), large_view(sat(0.99))
    assert verdict(s, g) == C.CAPACITY
    assert verdict(s, g, ref_ok=False) == C.NOT_EVALUATED
    assert verdict(s, g, leakage=True) == C.NOT_EVALUATED


def test_row2_dependence_failed() -> None:
    s = view(sat(0.35), RUN_SMALL, extra=(3 * U_P,), chance_disabled=False)
    assert verdict(s, large_view(sat(0.99))) == C.DEPENDENCE_FAILED
    g = view(sat(0.99), RUN_LARGE, chance_disabled=False)
    assert verdict(small_view(sat(0.35)), g) == C.DEPENDENCE_FAILED


def test_row3_ceiling_row4_capacity_and_its_five_conditions() -> None:
    assert verdict(small_view(sat(0.97)), large_view(sat(0.99))) == C.CEILING  # i(N; U_P) >= 4.5
    s, g = small_view(sat(0.35)), large_view(sat(0.99))
    assert verdict(s, g) == C.CAPACITY
    assert verdict(s, g, MC_SHORT) == C.GAIN_ONLY  # no matched-compute readout: Delta_MC is not established
    assert verdict(s, g, C.McEntry(C.MC_AMBIGUOUS, None, None, 1.0, None)) == C.GAIN_ONLY
    # smaller cell not loaded (i* above 4.0, below the ceiling): GAIN WITHIN BUDGET ONLY, not CAPACITY
    assert verdict(small_view(sat(0.92)), large_view(sat(1.0, 700.0))) == C.GAIN_ONLY
    # smaller cell not plateaued (still rising across the second half of its run): not loaded
    slow = lambda u: 0.55 * u / RUN_SMALL  # noqa: E731
    assert not small_view(slow).loaded()
    assert verdict(small_view(slow), large_view(sat(0.99))) == C.GAIN_ONLY
    # the larger cell must reach a_use 0.5
    assert verdict(small_view(sat(0.0)), large_view(sat(0.45))) != C.CAPACITY


def test_row4_two_doublings_condition() -> None:
    """Delta_SAT - 2 [i*(N; U_run) - i*(N; U_run/2)] >= 0.5: a smaller cell that still creeps up by 0.1 per half-run loses a gap of 0.55."""
    small = view(lambda u: 0.30 + 4e-7 * u if u <= RUN_SMALL else 0.0, RUN_SMALL, extra=(3 * U_P,))
    gain = small.i_star(RUN_SMALL)[0] - small.i_star(RUN_SMALL // 2)[0]
    assert 0.0 < gain <= core.PLATEAU_MAX
    big = large_view(sat(0.99))
    d_sat = big.i(U_P) - small.i_star(RUN_SMALL)[0]
    expected = C.CAPACITY if C.ge(d_sat - 2.0 * gain, core.GAIN_MIN) else C.GAIN_ONLY
    assert verdict(small, big) == expected


def test_rows_5_to_10() -> None:
    assert verdict(small_view(sat(0.45)), large_view(sat(0.2))) == C.REVERSED  # d_mu and d_full both <= -0.5
    late = lambda u: 0.99 * (1.0 - math.exp(-u / 6000.0)) if u <= RUN_LARGE else 0.0  # noqa: E731
    behind = verdict(small_view(sat(0.80)), large_view(late))
    assert behind in (C.BEHIND, C.REVERSED, C.UNRESOLVED) and behind != C.CAPACITY
    # a clean BEHIND WITHIN BUDGET: slower larger cell that catches up by its run length
    fast_small = small_view(sat(0.80, 300.0))
    slow_large = large_view(lambda u: 0.80 * (1.0 - math.exp(-u / 9000.0)))
    d = C.capacity_panel(fast_small, slow_large, MC_OK, ref_ok=True)
    assert d.detail["delta_mu"] <= -core.GAIN_MIN and d.detail["delta_full"] > -core.GAIN_MIN and d.verdict == C.BEHIND
    assert verdict(small_view(sat(0.60)), large_view(sat(0.60))) == C.NULL  # |d| < 0.25, plateaued, loaded
    assert verdict(small_view(sat(0.93)), large_view(sat(0.93))) == C.FLAT_NOT_LOADED  # plateaued, i* in (4.0, 4.5)
    assert verdict(small_view(sat(0.60)), large_view(sat(0.68))) == C.UNRESOLVED  # 0.25 <= |d| < 0.5


def test_panel_disagree_and_first_match() -> None:
    a = C.capacity_panel(small_view(sat(0.35)), large_view(sat(0.99)), MC_OK, ref_ok=True)
    b = C.capacity_panel(small_view(sat(0.60)), large_view(sat(0.60)), MC_OK, ref_ok=True)
    assert C.capacity_replicate({"A": a, "B": a}).verdict == C.CAPACITY
    assert C.capacity_replicate({"A": a, "B": b}).verdict == C.PANEL_DISAGREE
    assert C.capacity_replicate({"A": a, "B": b}).detail["panels"]["B"]["verdict"] == C.NULL


def test_loaded_is_the_one_definition() -> None:
    v = small_view(sat(0.5))
    assert v.plateaued() and v.loaded() and v.i_star(v.run)[0] <= core.LOADED_I_MAX
    assert not small_view(sat(0.93)).loaded()
    assert not small_view(lambda u: 0.55 * u / RUN_SMALL).loaded()


# --- capacity: classes (enumerated) -------------------------------------------------------------------------------------------------------
VERDICTS = [C.NOT_EVALUATED, C.DEPENDENCE_FAILED, C.PANEL_DISAGREE, C.CAPACITY, C.GAIN_ONLY, C.CEILING, C.FLAT_NOT_LOADED, C.REVERSED, C.NULL, C.BEHIND, C.UNRESOLVED]


def reference_step_class(v: list[str]) -> str:
    n = 5
    count = lambda *names: sum(1 for x in v if x in names)  # noqa: E731
    if count(C.NOT_EVALUATED) >= 2:
        return C.NOT_EVALUATED
    if count(C.DEPENDENCE_FAILED) >= 2:
        return C.DEPENDENCE_FAILED
    if count(C.PANEL_DISAGREE) >= 2:
        return C.NOT_REPLICATED
    if count(C.CAPACITY) == n:
        return C.CAPACITY_STEP
    if count(C.CAPACITY, C.GAIN_ONLY) == n:
        return C.GAIN_STEP
    if count(C.CEILING, C.FLAT_NOT_LOADED) >= 4:
        return C.NOT_LOADED
    if count(C.REVERSED) >= 4:
        return C.REVERSED
    if count(C.NULL, C.REVERSED) >= 4:
        return C.NO_GAIN
    return C.MIXED


def test_step_class_over_all_replicate_combinations() -> None:
    seen: set[str] = set()
    for combo in itertools.product(VERDICTS, repeat=5):
        got = C.capacity_step_class(list(combo))
        assert got == reference_step_class(list(combo))
        seen.add(got)
    assert seen == {C.NOT_EVALUATED, C.DEPENDENCE_FAILED, C.NOT_REPLICATED, C.CAPACITY_STEP, C.GAIN_STEP, C.NOT_LOADED, C.REVERSED, C.NO_GAIN, C.MIXED}
    with pytest.raises(ValueError):
        C.capacity_step_class([C.CAPACITY] * 4)  # the denominator is always 5


TRANSITIONS = {"4K→16K": ["A1", "B1"], "16K→64K": ["A2", "B2"]}
STEP_CLASSES = [C.NOT_EVALUATED, C.DEPENDENCE_FAILED, C.NOT_REPLICATED, C.CAPACITY_STEP, C.GAIN_STEP, C.NOT_LOADED, C.REVERSED, C.NO_GAIN, C.MIXED]


def reference_arm_class(c: dict[str, str], a_use_ok: bool) -> str:
    per = {t: [c[s] for s in ss] for t, ss in TRANSITIONS.items()}
    if any(all(x == C.NOT_EVALUATED for x in xs) for xs in per.values()):
        return C.NOT_EVALUATED
    if any(x == C.DEPENDENCE_FAILED for x in c.values()):
        return C.DEPENDENCE_FAILED
    has = [any(x == C.CAPACITY_STEP for x in xs) for xs in per.values()]
    if all(has) and C.REVERSED not in c.values() and a_use_ok:
        return C.CAPACITY_SUPPORTED
    if any(has):
        return C.CAPACITY_ONE_TRANSITION
    if any(all(x == C.NOT_LOADED for x in xs) for xs in per.values()):
        return C.NOT_TESTED_BY_LOAD
    if all(any(x in (C.NO_GAIN, C.REVERSED) for x in xs) for xs in per.values()):
        return C.CAPACITY_NOT_SUPPORTED
    return C.INTERMEDIATE


def test_arm_class_enumerated() -> None:
    seen: set[str] = set()
    for combo in itertools.product(STEP_CLASSES, repeat=4):
        c = dict(zip(("A1", "B1", "A2", "B2"), combo, strict=True))
        for ok in (True, False):
            got = C.capacity_arm_class(c, TRANSITIONS, ok)
            assert got == reference_arm_class(c, ok)
            seen.add(got)
    assert seen == {C.NOT_EVALUATED, C.DEPENDENCE_FAILED, C.CAPACITY_SUPPORTED, C.CAPACITY_ONE_TRANSITION, C.NOT_TESTED_BY_LOAD, C.CAPACITY_NOT_SUPPORTED, C.INTERMEDIATE}


# --- control and cost labels ------------------------------------------------------------------------------------------------------------------
def dense_cell(d: float, r: float | None, dense_a: float = 0.4, reps: int = 5, mc: tuple[float, float | None] | None = None, replicates_with_d: int = 5) -> C.DenseCell:
    def rep(k: int) -> dict[str, dict[str, tuple[float, float | None, float]]]:
        dd = d if k < replicates_with_d else 0.0
        base = {p: (dd, r, dense_a) for p in core.PANELS}
        other = {p: ((mc[0] if mc else dd), (mc[1] if mc else r), dense_a) for p in core.PANELS}
        return {"MU": base, "MC": other, "D-BEST": base}

    return C.DenseCell("A1", [rep(k) for k in range(reps)])


def test_dense_labels() -> None:
    assert C.dense_label([dense_cell(-0.3, 0.9)])["label"] == C.DENSE_AHEAD
    assert C.dense_label([dense_cell(-0.3, 0.9, replicates_with_d=3)])["label"] != C.DENSE_AHEAD  # only 3 of 5 replicates
    assert C.dense_label([dense_cell(-0.3, 0.9, replicates_with_d=4)])["label"] == C.DENSE_AHEAD  # 4 of 5 suffices
    assert C.dense_label([dense_cell(1.0, 1.2)])["label"] == C.BEATS_DENSE
    assert C.dense_label([dense_cell(1.0, 1.05)])["label"] == C.DENSE_MATCHES
    assert C.dense_label([dense_cell(1.0, 1.2, mc=(0.0, 1.0))])["label"] == C.DENSE_MATCHES  # r >= 1.10 needed under MC too
    assert C.dense_label([dense_cell(1.0, None, dense_a=0.03)])["label"].startswith(C.BEATS_DENSE) and "DENSE AT CHANCE" in C.dense_label([dense_cell(1.0, None, dense_a=0.03)])["label"]
    assert C.dense_label([], ["8K/64K"])["label"] == C.DENSE_NOT_READ
    # DENSE AHEAD takes precedence over every other label, and is read in any one reading
    ahead_mc_only = dense_cell(1.0, 1.2, mc=(-0.4, 0.8))
    assert C.dense_label([ahead_mc_only])["label"] == C.DENSE_AHEAD
    assert C.dense_reading(4.0, 0.0, N) == (4.0, None)


def test_active_work_hierarchy_and_conventional_labels() -> None:
    assert C.active_work_label(66816, 263424) == C.LINEAR_KEY_SCORING and C.active_work_label(9728, 10496) == C.SUBLINEAR and C.active_work_label(100, 200) == C.SUBLINEAR
    rep = lambda x: {"8K/16K": dict.fromkeys(core.PANELS, x), "32K/64K": dict.fromkeys(core.PANELS, x)}  # noqa: E731
    assert C.hierarchy_label([rep(1.05)] * 5) == C.TREE_AHEAD
    assert C.hierarchy_label([rep(1.05)] * 4 + [rep(0.5)]) == C.TREE_AHEAD  # 4 of 5
    assert C.hierarchy_label([rep(0.99)] * 5) == C.TREE_COMPETITIVE
    assert C.hierarchy_label([rep(0.9)] * 5) == C.TREE_BEHIND
    arm = [dict.fromkeys(core.PANELS, 4.0)] * 5
    assert C.conventional_suffices(arm, [dict.fromkeys(core.PANELS, 3.8)] * 5, [dict.fromkeys(core.PANELS, 0.0)] * 5)
    assert not C.conventional_suffices(arm, [dict.fromkeys(core.PANELS, 3.0)] * 5, [dict.fromkeys(core.PANELS, 3.0)] * 5)
    assert C.key_learning_limited(C.CAPACITY_SUPPORTED, C.INTERMEDIATE) and not C.key_learning_limited(C.CAPACITY_SUPPORTED, C.CAPACITY_SUPPORTED)


def test_robustness_and_held_out_labels_and_study_b_is_retired() -> None:
    assert C.robustness_label([0.06] * 5) == "RISES WITH SLOTS" and C.robustness_label([0.06] * 4 + [0.0]) == "UNCHANGED"
    assert C.robustness_label([-0.06] * 4 + [0.1]) == "FALLS" and C.robustness_label([0.0] * 5) == "UNCHANGED"
    assert C.held_out_fragile(0.80, 0.95) and not C.held_out_fragile(0.90, 0.95)
    assert not hasattr(C, "study_b_label")  # retired in revision 5: the saturation line (section 8.10) replaces it


# --- capacity outcome: an unevaluated or untested study is never a negative ---------------------------------------------------------------------
ARM_CLASSES = [C.NOT_EVALUATED, C.DEPENDENCE_FAILED, C.NOT_TESTED_BY_LOAD, C.CAPACITY_ONE_TRANSITION, C.INTERMEDIATE, C.CAPACITY_NOT_SUPPORTED, C.CAPACITY_SUPPORTED]
DENSE_LABELS = [C.DENSE_AHEAD, C.BEATS_DENSE, C.DENSE_MATCHES, C.DENSE_NOT_READ]


def arms_of(classes: tuple[str, str, str], dense: tuple[str, str, str] = (C.DENSE_MATCHES,) * 3) -> dict[str, C.ArmCapacity]:
    return {a: C.ArmCapacity(a, c, d) for a, c, d in zip(core.LEARNED_KEY_ARMS, classes, dense, strict=True)}


def reference_outcome_row(classes: tuple[str, str, str], dense: tuple[str, str, str], every_not_loaded: bool = False) -> int:
    arms = dict(zip(core.LEARNED_KEY_ARMS, zip(classes, dense, strict=True), strict=True))
    supported = [a for a, (c, d) in arms.items() if c == C.CAPACITY_SUPPORTED]
    if any(arms[a][1] not in (C.DENSE_AHEAD, C.DENSE_NOT_READ) for a in supported):
        return 3
    if (arms["F-OQ"][0] == C.CAPACITY_NOT_SUPPORTED and arms["T-OQ"][0] == C.CAPACITY_NOT_SUPPORTED) or (supported and all(arms[a][1] == C.DENSE_AHEAD for a in supported)):
        return 4
    return 5 if every_not_loaded else 6


def test_outcome_rows_enumerated() -> None:
    hits: set[int] = set()
    for classes in itertools.product(ARM_CLASSES, repeat=3):
        for dense in itertools.product(DENSE_LABELS, repeat=3):
            for enl in (False, True):
                out = C.capacity_outcome(arms_of(classes, dense), engineering_failed=False, incomplete=False, every_step_not_loaded=enl)
                assert out.row == reference_outcome_row(classes, dense, enl), (classes, dense, enl)
                hits.add(out.row)
    assert hits == {3, 4, 5, 6}


def test_no_arm_supported_is_never_negative_unless_both_not_supported() -> None:
    """Every arm in turn NOT_EVALUATED, DEPENDENCE_FAILED, NOT_TESTED_BY_LOAD, CAPACITY_ONE_TRANSITION, INTERMEDIATE: CAPACITY-INCONCLUSIVE (or NOT TESTED), never CAPACITY-NEGATIVE."""
    for cls in (C.NOT_EVALUATED, C.DEPENDENCE_FAILED, C.NOT_TESTED_BY_LOAD, C.CAPACITY_ONE_TRANSITION, C.INTERMEDIATE):
        for mix in itertools.product((cls, C.CAPACITY_ONE_TRANSITION, C.INTERMEDIATE, C.NOT_EVALUATED), repeat=3):
            out = C.capacity_outcome(arms_of(mix), engineering_failed=False, incomplete=False)
            assert out.label == C.CAPACITY_INCONCLUSIVE and out.reasons
        out = C.capacity_outcome(arms_of((cls, cls, cls)), engineering_failed=False, incomplete=False, every_step_not_loaded=cls == C.NOT_TESTED_BY_LOAD)
        assert out.label in (C.CAPACITY_INCONCLUSIVE, C.CAPACITY_NOT_TESTED) and out.label != C.CAPACITY_NEGATIVE
    # unevaluated everywhere: empty set never satisfies (b)
    out = C.capacity_outcome(arms_of((C.NOT_EVALUATED,) * 3), engineering_failed=False, incomplete=False)
    assert out.label == C.CAPACITY_INCONCLUSIVE
    # a CAPACITY_SUPPORTED arm with no D-OQ read can neither make the positive nor the negative
    out = C.capacity_outcome(arms_of((C.CAPACITY_SUPPORTED, C.INTERMEDIATE, C.INTERMEDIATE), (C.DENSE_NOT_READ,) * 3), engineering_failed=False, incomplete=False)
    assert out.label == C.CAPACITY_INCONCLUSIVE and any("DENSE NOT READ" in r for r in out.reasons)
    assert C.capacity_outcome(arms_of((C.CAPACITY_NOT_SUPPORTED,) * 3), engineering_failed=False, incomplete=False).label == C.CAPACITY_NEGATIVE
    assert C.capacity_outcome(arms_of((C.CAPACITY_NOT_SUPPORTED, C.INTERMEDIATE, C.INTERMEDIATE)), engineering_failed=False, incomplete=False).label == C.CAPACITY_INCONCLUSIVE
    assert C.capacity_outcome(arms_of((C.CAPACITY_SUPPORTED,) * 3, (C.DENSE_AHEAD,) * 3), engineering_failed=False, incomplete=False).label == C.CAPACITY_NEGATIVE
    assert C.capacity_outcome(arms_of((C.CAPACITY_SUPPORTED, C.CAPACITY_SUPPORTED, C.INTERMEDIATE), (C.DENSE_AHEAD, C.BEATS_DENSE, C.DENSE_MATCHES)), engineering_failed=False, incomplete=False).label == C.CAPACITY_POSITIVE


def test_engineering_failure_and_incomplete_come_first() -> None:
    arms = arms_of((C.CAPACITY_SUPPORTED,) * 3)
    assert C.capacity_outcome(arms, engineering_failed=True, incomplete=True).label == C.S1_ENGINEERING_FAILURE
    assert C.capacity_outcome(arms, engineering_failed=False, incomplete=True).label == C.S1_INCOMPLETE
    assert C.efficiency_outcome({}, {}, engineering_failed=True, incomplete=False).label == C.S1_ENGINEERING_FAILURE
    assert C.efficiency_outcome({}, {}, engineering_failed=False, incomplete=True).label == C.S1_INCOMPLETE


def test_milestone_reading() -> None:
    def full(classes: tuple[str, str, str], dense: tuple[str, str, str] = (C.DENSE_MATCHES,) * 3, sat: str = C.SAT_PROPORTIONAL_ALL_PAIRS, dense_sat: str = C.SAME_AT_SATURATION) -> dict[str, C.ArmCapacity]:
        return {a: C.ArmCapacity(a, c, d, sat_class=sat, dense_sat=dense_sat) for a, c, d in zip(core.LEARNED_KEY_ARMS, classes, dense, strict=True)}

    work = {"F-OQ": C.LINEAR_KEY_SCORING, "T-OQ": C.SUBLINEAR, "F-OQ-IVF": C.SUBLINEAR}
    arms = full((C.CAPACITY_SUPPORTED,) * 3)
    out = C.capacity_outcome(arms, engineering_failed=False, incomplete=False)
    assert "16,384→65,536 NOT TESTED" in out.printed and "1,024 TO 16,384 SLOTS" in out.printed
    sub = C.milestone_reading(out, arms, work, C.TREE_AHEAD, "S0 NOT YET DECIDED")
    assert "Storage half supported, as a necessary condition, from 1,024 to 16,384 slots [" in sub and core.STORE_ONLY_TAG in sub and "S0 NOT YET DECIDED" in sub and core.ORACLE_SENTENCE in sub
    # refused without the saturation class, with DENSE HOLDS MORE AT SATURATION, and with an unestablished matched-compute reading (either dense label)
    no_sat = C.milestone_reading(out, full((C.CAPACITY_SUPPORTED,) * 3, sat=C.INTERMEDIATE), work, C.TREE_AHEAD, "S0 X")
    assert "Storage half supported" not in no_sat and no_sat.startswith("Capacity steps shown; proportional saturation not shown") and core.STORE_ONLY_TAG in no_sat and "INTERMEDIATE" in no_sat
    holds = full((C.CAPACITY_SUPPORTED,) * 3, dense_sat=C.DENSE_HOLDS_MORE)
    out_h = C.capacity_outcome(holds, engineering_failed=False, incomplete=False)
    assert out_h.label == C.CAPACITY_NEGATIVE and "(b: DENSE AHEAD)" in out_h.printed and "16,384→65,536 NOT TESTED" in out_h.printed  # DENSE HOLDS MORE counts as DENSE AHEAD
    assert C.milestone_reading(out_h, holds, work, C.TREE_AHEAD, "S0 X").startswith("Storage half not supported")
    notest = full((C.CAPACITY_SUPPORTED,) * 3, (C.DENSE_MATCHES, f"{C.DENSE_NOT_ESTABLISHED} (MC-SHORT)", f"{C.DENSE_NOT_ESTABLISHED} (MC-SHORT)"))
    r_no = C.milestone_reading(C.capacity_outcome(notest, engineering_failed=False, incomplete=False), notest, work, C.TREE_AHEAD, "S0 X")
    assert r_no.startswith("Storage-half reading not available") and "Storage half supported" not in r_no
    sub_not = full((C.CAPACITY_SUPPORTED,) * 3)
    for a in sub_not.values():
        a.dense_sat_sublabels = [C.DENSE_NOT_ESTABLISHED]  # the matched-compute reading at saturation is not established either: the conservative reading refuses
    assert C.milestone_reading(out, sub_not, work, C.TREE_AHEAD, "S0 X").startswith("Storage-half reading not available")
    only = C.milestone_reading(out, arms, {"F-OQ": C.LINEAR_KEY_SCORING, "T-OQ": C.LINEAR_KEY_SCORING, "F-OQ-IVF": C.LINEAR_KEY_SCORING}, C.TREE_BEHIND, "S0 NOT YET DECIDED")
    assert only.startswith("Capacity shown; sublinear active work not shown") and core.STORE_ONLY_TAG in only
    neg = C.capacity_outcome(arms_of((C.CAPACITY_NOT_SUPPORTED,) * 3), engineering_failed=False, incomplete=False)
    assert C.milestone_reading(neg, arms, {}, C.TREE_BEHIND, "S0 X").startswith("Storage half not supported for this store, backbone, task and budget")
    inc = C.capacity_outcome(arms_of((C.INTERMEDIATE,) * 3), engineering_failed=False, incomplete=False)
    assert C.milestone_reading(inc, arms, {}, C.TREE_BEHIND, "S0 X").startswith("Not established")
    ahead = full((C.CAPACITY_SUPPORTED,) * 3, (C.BEATS_DENSE, C.DENSE_AHEAD, C.DENSE_AHEAD))
    out2 = C.capacity_outcome(ahead, engineering_failed=False, incomplete=False)
    assert out2.label == C.CAPACITY_POSITIVE
    assert "Capacity shown; sublinear active work not shown" in C.milestone_reading(out2, ahead, work, C.TREE_AHEAD, "S0 X")


# --- the tag ------------------------------------------------------------------------------------------------------------------------------------
def test_every_positive_label_needs_the_tag() -> None:
    for label in C.POSITIVE_LABELS:
        assert C.is_positive(label)
        with pytest.raises(C.UntaggedPositiveLabel):
            C.emit(f"result: {label}")
        assert core.STORE_ONLY_TAG in C.tagged(label)
        assert C.emit(C.tagged(label)) == C.tagged(label)
        assert C.emit(C.printable(label)) and core.STORE_ONLY_TAG in C.printable(label)
        assert C.emit(C.tag_positives(f"text {label} text")) and C.untagged_positive_labels(C.tag_positives(f"x {label} y")) == []
    for label in (C.CAPACITY_NEGATIVE, C.CAPACITY_INCONCLUSIVE, C.CAPACITY_NOT_TESTED, C.EFFICIENCY_NEGATIVE, "DENSE AHEAD", "DENSE MATCHES", "TREE_BEHIND", "NOT_EVALUATED", C.S1_INCOMPLETE):
        assert not C.is_positive(label) and C.emit(label) == label
    assert C.emit("CAPACITY-POSITIVE [STORE ONLY; ORACLE-ADDRESSED; arm F-OQ; hierarchy TREE_AHEAD]")  # a label listed inside a tagged bracket is covered
    with pytest.raises(C.UntaggedPositiveLabel):
        C.emit("CAPACITY-POSITIVE [WITHIN REGISTERED RUN LENGTHS]")
    with pytest.raises(C.UntaggedPositiveLabel):
        C.emit("a tagged label [STORE ONLY; ORACLE-ADDRESSED] and BEATS DENSE alone")


def test_no_outcome_can_carry_a_positive_label_without_the_tag() -> None:
    """Every outcome of both lines, over every arm-class combination, prints through ``emit``: a positive label never appears bare."""
    for classes in itertools.product(ARM_CLASSES, repeat=3):
        for dense in itertools.product(DENSE_LABELS, repeat=3):
            out = C.capacity_outcome(arms_of(classes, dense), engineering_failed=False, incomplete=False)
            assert C.untagged_positive_labels(out.printed) == []
            assert C.untagged_positive_labels(C.milestone_reading(out, arms_of(classes, dense), {a: C.SUBLINEAR for a in core.LEARNED_KEY_ARMS}, C.TREE_AHEAD, "S0 X")) == []
            if out.label == C.CAPACITY_POSITIVE:
                assert core.STORE_ONLY_TAG in out.printed and "WITHIN REGISTERED RUN LENGTHS" in out.printed
    for cs in itertools.product(("EFFICIENCY_SUPPORTED", "EFFICIENCY_NOT_SUPPORTED", "EFFICIENCY_ONE_TRANSITION", C.INTERMEDIATE), repeat=2):
        for d in itertools.product(("DENSE FASTER", "DENSE NOT FASTER", C.DENSE_NOT_READ), repeat=2):
            out = C.efficiency_outcome(dict(zip(core.EFFICIENCY_ARMS, cs, strict=True)), dict(zip(core.EFFICIENCY_ARMS, d, strict=True)), engineering_failed=False, incomplete=False)
            assert C.untagged_positive_labels(out.printed) == []


# --- matched compute ---------------------------------------------------------------------------------------------------------------------------------
def test_matched_compute_snapshot_rule() -> None:
    cheap = {"cpu": 1.0, "madds": 1.0}
    assert C.mc_pair(cheap, {"cpu": 1.0, "madds": 1.0}, U_P, RUN_SMALL, RUN_LARGE) == C.McEntry("OK", U_P, U_P, 1.0, "small")  # equal costs: not a disagreement
    e = C.mc_pair(cheap, {"cpu": 2.2, "madds": 3.9}, U_P, RUN_SMALL, RUN_LARGE)  # the larger multiplier (3.9) is used: grid value 4
    assert (e.status, e.small_update, e.large_update, e.cheaper, e.annotation) == ("OK", 4 * U_P, U_P, "small", None) and e.multiplier == pytest.approx(3.9)
    assert C.mc_pair(cheap, {"cpu": 1.1, "madds": 1.1}, U_P, RUN_SMALL, RUN_LARGE).small_update == int(1.25 * U_P)
    assert C.mc_pair(cheap, {"cpu": 6.0, "madds": 1.0}, U_P, RUN_SMALL, RUN_LARGE).small_update == 6 * U_P
    short = C.mc_pair(cheap, {"cpu": 5.0, "madds": 1.0}, U_P, 4 * U_P, RUN_LARGE)  # 5x needs the grid value 6 > the cheaper cell's 4 U_P
    assert short.status == C.MC_SHORT and short.small_update is None and not short.ok()
    assert C.mc_pair(cheap, {"cpu": 7.0, "madds": 1.0}, U_P, 8 * U_P, RUN_LARGE).status == C.MC_SHORT  # beyond the grid
    flip = C.mc_pair({"cpu": 2.0, "madds": 2.0}, {"cpu": 1.0, "madds": 1.0}, U_P, RUN_SMALL, RUN_LARGE)  # the smaller cell is costlier: the larger is the cheaper one
    assert flip.cheaper == "large" and flip.small_update == U_P and flip.large_update == 2 * U_P


def test_a_disagreement_of_the_cost_measures_is_read_in_the_comparators_favour() -> None:
    # section 5.4 (revision 5): the cell whose advantage would be claimed is read at U_P, the other at the smallest grid snapshot with multiplier >= max(r, 1/r) over both measures; no fixture sets the
    # 1,024-slot cost equal to the 4,096-slot cost (review m10)
    small, large = {"cpu": 1.0, "madds": 2.0}, {"cpu": 2.0, "madds": 1.0}  # cpu: large costs 2x; madds: small costs 2x
    cap = C.mc_pair(small, large, U_P, RUN_SMALL, RUN_LARGE, "large")  # capacity line: the larger cell's advantage is claimed
    assert (cap.status, cap.annotation, cap.large_update, cap.small_update, cap.cheaper) == ("OK", C.MC_AMBIGUOUS, U_P, 2 * U_P, "small") and cap.ok()
    dense = C.mc_pair({"cpu": 1.0, "madds": 2.0}, {"cpu": 2.0, "madds": 1.0}, U_P, RUN_SMALL, RUN_LARGE, "small")  # dense labels: role small is the memory arm, role large is D-OQ
    assert (dense.status, dense.annotation, dense.small_update, dense.large_update, dense.cheaper) == ("OK", C.MC_AMBIGUOUS, U_P, 2 * U_P, "large")
    wide = C.mc_pair({"cpu": 1.0, "madds": 3.0}, {"cpu": 1.2, "madds": 1.0}, U_P, RUN_SMALL, RUN_LARGE, "large")  # max(r, 1/r) = 3 -> the grid value 3
    assert wide.small_update == 3 * U_P and wide.large_update == U_P and wide.annotation == C.MC_AMBIGUOUS
    assert C.mc_pair({"cpu": 1.0, "madds": 6.5}, {"cpu": 1.2, "madds": 1.0}, U_P, 8 * U_P, RUN_LARGE, "large").status == C.MC_SHORT  # beyond the grid
    assert C.mc_pair({"cpu": 1.0, "madds": 5.0}, {"cpu": 1.2, "madds": 1.0}, U_P, 4 * U_P, RUN_LARGE, "large").status == C.MC_SHORT  # the snapshot exceeds the other cell's run length
    assert C.mc_pair(small, large, U_P, RUN_SMALL, RUN_LARGE, "small").large_update == 2 * U_P  # the claimed cell differs: the other cell is the one read late
    near = C.mc_pair({"cpu": 1.0, "madds": 1.0}, {"cpu": 1.0 + 1e-14, "madds": 1.0 - 1e-14}, U_P, RUN_SMALL, RUN_LARGE)
    assert near.annotation is None and near.ok()  # equal cost within EPS in both measures is not a disagreement


# --- efficiency line ---------------------------------------------------------------------------------------------------------------------------------
def test_u_t_interpolates_on_log_updates_and_censors() -> None:
    profile = lambda u: min(0.99, 0.0 + 0.2 * math.log2(u / 256.0) / 1.0) if u >= 256 else 0.0  # noqa: E731
    v = view(lambda u: 0.62 if u == 2048 else (0.30 if u == 1024 else (0.99 if u >= 4096 else (0.1 if u <= 512 else 0.8))), RUN_LARGE)
    res = C.u_t([v, v])
    assert res.ut.kind == "exact" and res.s_hit is not None and res.s_prev is not None and res.s_prev < res.ut.lo <= res.s_hit
    i_prev, i_hit = v.i(res.s_prev), v.i(res.s_hit)
    x = math.log2(res.s_prev) + (3.0 - i_prev) / (i_hit - i_prev) * (math.log2(res.s_hit) - math.log2(res.s_prev))
    assert res.ut.lo == pytest.approx(2.0**x)
    assert profile(256) == 0.0 and profile(512) == pytest.approx(0.2)
    left = C.u_t([view(lambda u: 0.99, RUN_LARGE)] * 2)
    assert left.ut.kind == "left" and left.ut.lo == 0.0 and left.ut.hi == float(min(view(lambda u: 0.99, RUN_LARGE).updates))
    right = C.u_t([view(lambda u: 0.2, RUN_LARGE)] * 2)
    assert right.ut.kind == "right" and right.ut.lo == float(RUN_LARGE) and right.ut.hi == math.inf
    # both panels must reach 3.0 bits: the minimum of the two decides
    low = view(lambda u: 0.2, RUN_LARGE)
    assert C.u_t([view(lambda u: 0.99, RUN_LARGE), low]).ut.kind == "right"
    # DEP failing at the first snapshot with i >= i_T on both panels, no earlier snapshot qualifying
    bad = view(lambda u: 0.99, RUN_LARGE, chance_disabled=False)
    assert C.u_t([bad, bad]).dep_failed


def ut(kind: str, lo: float, hi: float) -> C.UTResult:
    return C.UTResult(C.UT(kind, lo, hi), False, None, None)


COSTS_S = {"cpu": 1.0, "madds": 1.0}
COSTS_L = {"cpu": 1.6, "madds": 1.3}


def brute_rows(small: C.UT, large: C.UT, run_small: int, run_large: int, cost_s: dict, cost_l: dict) -> dict[int, bool]:
    """Rows 4 to 7 of section 8.8 read 'for every value the bounds allow' by sampling both intervals (an independent check of the sup/inf comparisons)."""

    def samples(u: C.UT) -> list[float]:
        if u.kind == "exact":
            return [u.lo]
        if u.kind == "left":  # (0, hi]
            return [u.hi * f for f in (1e-9, 1e-3, 0.25, 0.5, 0.75, 0.999, 1.0)]
        return [u.lo * (1.0 + f) + 1e-9 for f in (1e-9, 1e-3, 0.5, 1.0, 10.0, 1e3, 1e6)]

    xs, ys = samples(large), samples(small)
    allp = lambda f: all(f(x, y) for x in xs for y in ys)  # noqa: E731
    return {
        4: small.kind == "right" and all(x <= run_small / 2 and all(x * cost_l[m] <= 0.8 * run_small * cost_s[m] for m in ("cpu", "madds")) for x in xs),
        5: allp(lambda x, y: x <= y / 2 and all(x * cost_l[m] <= 0.8 * y * cost_s[m] for m in ("cpu", "madds"))),
        6: allp(lambda x, y: x <= y / 2),
        7: allp(lambda x, y: x >= 2 * y) and (large.kind != "right" or run_large >= 2 * small.hi) and small.kind != "right",
    }


def test_efficiency_step_every_censoring_case_against_brute_force() -> None:
    cases_s = [ut("exact", 4000.0, 4000.0), ut("exact", 1000.0, 1000.0), ut("left", 0.0, 512.0), ut("left", 0.0, 2048.0), ut("right", float(RUN_SMALL), math.inf)]
    cases_l = [ut("exact", 100.0, 100.0), ut("exact", 1200.0, 1200.0), ut("exact", 9000.0, 9000.0), ut("exact", 20000.0, 20000.0), ut("left", 0.0, 512.0), ut("left", 0.0, 4096.0), ut("right", float(RUN_LARGE), math.inf), ut("exact", 24000.0, 24000.0)]
    seen: set[str] = set()
    for s, g in itertools.product(cases_s, cases_l):
        res = C.efficiency_step(s, g, ref_ok=True, leakage=False, run_small=RUN_SMALL, run_large=RUN_LARGE, cost_small=COSTS_S, cost_large=COSTS_L)
        rows = brute_rows(s.ut, g.ut, RUN_SMALL, RUN_LARGE, COSTS_S, COSTS_L)
        censored = s.ut.censored or g.ut.censored
        if s.ut.kind == "right" and g.ut.kind == "right":
            expected = C.NOT_ASSESSED
        elif rows[4]:
            expected = C.REACHED_ONLY
        elif rows[5]:
            expected = C.FASTER
        elif rows[6]:
            expected = C.FASTER_UPDATES_ONLY
        elif rows[7]:
            expected = C.SLOWER
        elif censored:
            expected = C.NOT_ASSESSED
        else:
            expected = C.SAME
        assert res.verdict == expected, (s.ut, g.ut, res.verdict, expected, rows)
        seen.add(res.verdict)
    assert seen >= {C.REACHED_ONLY, C.FASTER, C.SLOWER, C.SAME, C.NOT_ASSESSED}


def test_efficiency_row3_and_row8_are_exhaustive() -> None:
    """Revision 4's R1: a censored case with no condition of rows 4-7 holding for every value is NOT_ASSESSED; SAME needs both u_T known."""
    for s_kind, g_kind in itertools.product(("exact", "left", "right"), repeat=2):
        def mk(kind: str, run: float) -> C.UTResult:
            return {"exact": ut("exact", 3000.0, 3000.0), "left": ut("left", 0.0, 3000.0), "right": ut("right", run, math.inf)}[kind]

        res = C.efficiency_step(mk(s_kind, RUN_SMALL), mk(g_kind, RUN_LARGE), ref_ok=True, leakage=False, run_small=RUN_SMALL, run_large=RUN_LARGE, cost_small=COSTS_S, cost_large=COSTS_L)
        assert res.verdict in (C.REACHED_ONLY, C.FASTER, C.FASTER_UPDATES_ONLY, C.SLOWER, C.SAME, C.NOT_ASSESSED)
        if res.verdict == C.SAME:
            assert s_kind == "exact" and g_kind == "exact"
    assert C.efficiency_step(ut("exact", 3000.0, 3000.0), ut("exact", 3000.0, 3000.0), ref_ok=True, leakage=False, run_small=RUN_SMALL, run_large=RUN_LARGE, cost_small=COSTS_S, cost_large=COSTS_L).verdict == C.SAME
    # rows 1 and 2 first
    base = dict(run_small=RUN_SMALL, run_large=RUN_LARGE, cost_small=COSTS_S, cost_large=COSTS_L)
    assert C.efficiency_step(ut("exact", 1.0, 1.0), ut("exact", 1.0, 1.0), ref_ok=False, leakage=False, **base).verdict == C.NOT_EVALUATED
    assert C.efficiency_step(ut("exact", 1.0, 1.0), ut("exact", 1.0, 1.0), ref_ok=True, leakage=True, **base).verdict == C.NOT_EVALUATED
    failed = C.UTResult(C.UT("right", 1.0, math.inf), True, 512, None)
    assert C.efficiency_step(ut("exact", 1.0, 1.0), failed, ref_ok=True, leakage=False, **base).verdict == C.DEPENDENCE_FAILED


def test_efficiency_faster_needs_both_cost_measures() -> None:
    s, g = ut("exact", 4000.0, 4000.0), ut("exact", 1500.0, 1500.0)
    kw = dict(ref_ok=True, leakage=False, run_small=RUN_SMALL, run_large=RUN_LARGE)
    assert C.efficiency_step(s, g, cost_small={"cpu": 1.0, "madds": 1.0}, cost_large={"cpu": 1.0, "madds": 1.0}, **kw).verdict == C.FASTER
    assert C.efficiency_step(s, g, cost_small={"cpu": 1.0, "madds": 1.0}, cost_large={"cpu": 1.0, "madds": 3.0}, **kw).verdict == C.FASTER_UPDATES_ONLY  # compute not 0.8x in one measure
    assert C.efficiency_step(ut("exact", 1000.0, 1000.0), ut("exact", 2000.0, 2000.0), cost_small=COSTS_S, cost_large=COSTS_L, **kw).verdict == C.SLOWER
    # SLOWER with the larger cell right-censored needs U_run(4N) >= 2 u_T(N)
    assert C.efficiency_step(ut("exact", 3000.0, 3000.0), ut("right", float(RUN_LARGE), math.inf), cost_small=COSTS_S, cost_large=COSTS_L, **kw).verdict == C.SLOWER
    assert C.efficiency_step(ut("exact", 20000.0, 20000.0), ut("right", float(RUN_LARGE), math.inf), cost_small=COSTS_S, cost_large=COSTS_L, **kw).verdict == C.NOT_ASSESSED


EFF_VERDICTS = [C.NOT_EVALUATED, C.DEPENDENCE_FAILED, C.NOT_ASSESSED, C.REACHED_ONLY, C.FASTER, C.FASTER_UPDATES_ONLY, C.SLOWER, C.SAME]


def reference_eff_step_class(v: list[str]) -> str:
    count = lambda *names: sum(1 for x in v if x in names)  # noqa: E731
    if count(C.NOT_EVALUATED) >= 2:
        return C.NOT_EVALUATED
    if count(C.DEPENDENCE_FAILED) >= 2:
        return C.DEPENDENCE_FAILED
    if count(C.NOT_ASSESSED) >= 2:
        return C.NOT_ASSESSED
    if count(C.FASTER, C.REACHED_ONLY) == 5:
        return "FASTER STEP"
    if count(C.FASTER, C.FASTER_UPDATES_ONLY) == 5:
        return "UPDATES-ONLY STEP"
    if count(C.SLOWER) >= 4:
        return "SLOWER STEP"
    if count(C.SAME) >= 4:
        return "NO DIFFERENCE"
    return C.MIXED


def test_efficiency_classes_enumerated() -> None:
    seen = set()
    for combo in itertools.product(EFF_VERDICTS, repeat=5):
        got = C.efficiency_step_class(list(combo))
        assert got == reference_eff_step_class(list(combo))
        seen.add(got)
    assert seen >= {"FASTER STEP", "UPDATES-ONLY STEP", "SLOWER STEP", "NO DIFFERENCE", C.MIXED, C.NOT_EVALUATED, C.DEPENDENCE_FAILED, C.NOT_ASSESSED}
    # the open point of the ADR (section 20 item 5): REACHED ONLY and FASTER IN UPDATES ONLY mixed is MIXED
    assert C.efficiency_step_class([C.REACHED_ONLY, C.REACHED_ONLY, C.FASTER_UPDATES_ONLY, C.FASTER_UPDATES_ONLY, C.FASTER_UPDATES_ONLY]) == C.MIXED


def test_efficiency_arm_class_and_outcome() -> None:
    tr = {"4K→16K": ["A1", "B1"], "16K→64K": ["A2", "B2"]}
    fast = {s: "FASTER STEP" for s in ("A1", "B1", "A2", "B2")}
    assert C.efficiency_arm_class(fast, tr) == "EFFICIENCY_SUPPORTED"
    assert C.efficiency_arm_class({**fast, "B2": "SLOWER STEP"}, tr) == "EFFICIENCY_ONE_TRANSITION"
    assert C.efficiency_arm_class({s: "NO DIFFERENCE" for s in fast}, tr) == "EFFICIENCY_NOT_SUPPORTED"
    assert C.efficiency_arm_class({**fast, "A1": C.NOT_EVALUATED, "B1": C.NOT_ASSESSED}, tr) == C.NOT_EVALUATED
    assert C.efficiency_arm_class({**fast, "A1": C.DEPENDENCE_FAILED}, tr) == C.DEPENDENCE_FAILED
    assert C.efficiency_arm_class({s: C.MIXED for s in fast}, tr) == C.INTERMEDIATE
    arms = {"F-OQ": "EFFICIENCY_SUPPORTED", "T-OQ": C.INTERMEDIATE}
    assert C.efficiency_outcome(arms, {"F-OQ": "DENSE NOT FASTER"}, engineering_failed=False, incomplete=False).label == C.EFFICIENCY_POSITIVE
    assert C.efficiency_outcome(arms, {"F-OQ": "DENSE FASTER"}, engineering_failed=False, incomplete=False).label == C.EFFICIENCY_NEGATIVE
    assert C.efficiency_outcome({"F-OQ": C.INTERMEDIATE, "T-OQ": C.INTERMEDIATE}, {}, engineering_failed=False, incomplete=False).label == C.EFFICIENCY_INCONCLUSIVE  # an empty set never satisfies the second clause
    assert C.efficiency_outcome({"F-OQ": "EFFICIENCY_NOT_SUPPORTED", "T-OQ": "EFFICIENCY_NOT_SUPPORTED"}, {}, engineering_failed=False, incomplete=False).label == C.EFFICIENCY_NEGATIVE
    assert C.efficiency_outcome({"F-OQ": "EFFICIENCY_NOT_SUPPORTED", "T-OQ": C.INTERMEDIATE}, {}, engineering_failed=False, incomplete=False).label == C.EFFICIENCY_INCONCLUSIVE


def test_dense_faster_and_optimizer_assisted() -> None:
    both = lambda ut: [ut, ut]  # noqa: E731  (u_T per panel)
    arm = [both(C.UT("exact", 2000.0, 2000.0))] * 5
    fast = [both(C.UT("exact", 1000.0, 1000.0))] * 5
    c = {"cpu": 1.0, "madds": 1.0}
    assert C.dense_faster(arm, fast, c, c) == "DENSE FASTER"
    assert C.dense_faster(arm, [both(C.UT("exact", 1900.0, 1900.0))] * 5, c, c) == "DENSE NOT FASTER"
    assert C.dense_faster(arm, [both(C.UT("right", 8193.0, math.inf))] * 5, c, c) == "DENSE NOT FASTER"  # D-OQ never reached the level within its run: it cannot be faster
    assert C.dense_faster(arm, [None] * 5, c, c) == C.DENSE_NOT_READ
    assert C.dense_faster(arm, fast[:4] + [both(C.UT("exact", 9000.0, 9000.0))], c, c) == "DENSE FASTER"  # 4 of 5
    assert C.optimizer_assisted(0.2, 0.31) and not C.optimizer_assisted(0.2, 0.30) and not C.optimizer_assisted(0.0, 0.5)
    m = C.movement_ratios({"total": 10.0, "without_own_gradient": 4.0, "share_without": 0.4}, {"total": 30.0, "without_own_gradient": 18.0, "share_without": 0.6})
    assert m == {"total": 3.0, "without_own_gradient": 4.5, "share_without": pytest.approx(1.5)}
