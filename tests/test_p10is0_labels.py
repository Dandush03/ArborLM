# ruff: noqa: E501
"""P10IS0 labels (ADR-0023 sections 5.3, 6, 7): the eight combinations of 6.4, the combination of series, break points, and every combination of series states reaching exactly one headline of section 7."""

import itertools
import math
import sys
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from studies.p10is0 import core, labels  # noqa: E402
from studies.p10is0.labels import (  # noqa: E402
    FAILS,
    HOLDS,
    NOT_EVALUABLE,
    NOT_READ,
    CellResult,
    Convergence,
    RefFlags,
    SeriesAtLoad,
    TypeState,
    arm_class,
    type_state,
)

TH = core.Thresholds.from_config()
OK = CellResult(labels.SUCCEEDED)


def fail(*conds: int, lm: bool = False) -> CellResult:
    return CellResult(labels.FAILED, frozenset(conds), lm)


def results(*cells: CellResult) -> dict[int, CellResult]:
    return {i + 1: c for i, c in enumerate(cells)}


def test_eight_combinations_by_brute_force() -> None:
    seen: set[int] = set()
    for n_a, n_g, lm, stable, cond4 in itertools.product(range(0, 5), range(0, 5), (False, True), (False, True), (False, True)):
        if n_a + n_g > 10:
            continue
        cells = [fail(1) for _ in range(n_a)] + [fail(4) for _ in range(n_g)]
        cells += [OK] * (10 - len(cells))
        if lm:
            cells[-1] = CellResult(labels.SUCCEEDED, frozenset(), True)
            cells[-2] = CellResult(labels.SUCCEEDED, frozenset(), True)  # two flagged cells exceed the allowance of one
        cls = arm_class(results(*cells), TH)
        ts = type_state(cls, RefFlags(cond4=cond4), stable, TH)
        # expectation written out from the ADR's table, not from the code
        a = HOLDS if n_a <= 1 else FAILS
        if cond4:
            q = FAILS if (n_a >= 2 or lm or not stable) else NOT_EVALUABLE
            want = (a, NOT_EVALUABLE, q)
        else:
            g = NOT_READ if n_a >= 2 else (HOLDS if n_g <= 1 else FAILS)
            q = HOLDS if (n_a + n_g <= 1 and not lm and stable) else FAILS
            want = (a, g, q)
        assert (ts.a, ts.g, ts.q) == want
        seen.add(ts.combination)
    assert seen == {2, 3, 4, 5, 6, 7, 8}


def test_removed_or_not_evaluated_cell_type_is_combination_one() -> None:
    for flags in (RefFlags(other=(2,)), RefFlags(other=(3, 5)), RefFlags(cond4=True, other=(6,))):
        ts = type_state(arm_class(results(*[OK] * 10), TH), flags, True, TH)
        assert (ts.a, ts.g, ts.q, ts.combination) == (NOT_EVALUABLE, NOT_EVALUABLE, NOT_EVALUABLE, 1)
    ne = results(*[CellResult(labels.CELL_NOT_EVALUATED)] * 3, *[OK] * 7)
    assert arm_class(ne, TH).cls == labels.CLASS_NOT_EVALUATED
    assert type_state(arm_class(ne, TH), RefFlags(), True, TH).combination == 1
    assert type_state(None, RefFlags(), None, TH).combination == 1


def test_class_rules() -> None:
    assert arm_class(results(*[OK] * 9, fail(1)), TH).cls == labels.RELIABLE
    assert arm_class(results(*[OK] * 8, fail(1), fail(1)), TH).cls == labels.UNRELIABLE
    assert arm_class(results(*[OK] * 2, *[fail(1)] * 8), TH).cls == labels.CLASS_FAILS
    one_ne = results(CellResult(labels.CELL_NOT_EVALUATED), *[OK] * 9)
    assert arm_class(one_ne, TH).cls == labels.RELIABLE and arm_class(one_ne, TH).evaluated == 9


def test_address_stable_non_finite_counts_as_zero() -> None:
    assert labels.address_stable([0.9] * 10, TH)
    assert not labels.address_stable([0.9] * 5 + [math.nan] * 5, TH)  # median of five 0.9 and five 0 is 0.45
    assert labels.address_stable([0.9] * 6 + [None] * 4, TH)
    assert not labels.address_stable([], TH)


def test_combine_series() -> None:
    assert labels.combine_series([HOLDS, HOLDS], "Q") == HOLDS
    assert labels.combine_series([HOLDS, FAILS], "Q") == FAILS
    assert labels.combine_series([HOLDS, NOT_EVALUABLE], "Q") == NOT_EVALUABLE
    assert labels.combine_series([FAILS, NOT_EVALUABLE], "Q") == FAILS
    assert labels.combine_series([HOLDS, NOT_READ], "G") == FAILS
    assert labels.combine_series([HOLDS], "Q") == HOLDS


def test_break_point() -> None:
    b = labels.break_point({0.5: HOLDS, 1: HOLDS, 2: FAILS, 4: HOLDS})
    assert (b.l, b.l1, b.l1_state, b.non_monotone) == (1, 2, FAILS, True)
    b = labels.break_point({0.5: FAILS, 1: HOLDS})
    assert (b.l, b.l1, b.non_monotone) == (None, 0.5, True)
    b = labels.break_point({0.5: HOLDS, 1: HOLDS, 2: HOLDS, 4: HOLDS})
    assert (b.l, b.l1, b.l1_state) == (4, None, None)
    b = labels.break_point({0.5: HOLDS, 1: NOT_EVALUABLE, 2: NOT_EVALUABLE})
    assert (b.l, b.l1_state) == (0.5, NOT_EVALUABLE)


def test_plateau_and_confirmation_use_exact_fractions() -> None:
    f = Fraction
    assert labels.plateau_step_ok([f(50, 100), f(51, 100), f(52, 100)], TH)  # steps of exactly 0.01
    assert not labels.plateau_step_ok([f(50, 100), f(51, 100), f(53, 100)], TH)
    assert not labels.plateau_step_ok([f(50, 100), f(49, 100), f(47, 100)], TH)  # two-sided: a fall of 0.02 is not flat
    ok = labels.convergence_check(True, {"A5-D|P": [f(1, 100)] * 10, "A6|P": [f(0)] * 10}, TH)
    assert ok.status == labels.CONFIRMED and ok.tags == ()
    both = labels.convergence_check(True, {"x": [f(3, 100)] * 4, "y": [f(-3, 100)] * 4}, TH)
    assert both.tags == (labels.RISING, labels.DECLINING)
    assert labels.convergence_check(False, {"x": [f(0)]}, TH).tags == (labels.NOT_SHOWN,)
    assert labels.convergence_check(True, {"x": [f(2, 100)]}, TH).status == labels.CONFIRMED  # exactly 0.02 is within


def test_paired_sign_test() -> None:
    def pair(b: int, c: int, both: int = 0) -> dict[str, object]:
        a5 = results(*([OK] * b + [fail(1)] * c + [OK] * both))
        a0 = results(*([fail(1)] * b + [OK] * c + [OK] * both))
        return labels.paired(a5, a0, TH)

    assert pair(6, 0, 4)["label"] == labels.IMPROVES and pair(6, 0, 4)["pairs"] == 10
    assert pair(7, 1, 2)["label"] == labels.NOT_DISTINGUISHED  # d = 6 but p = 0.070
    assert pair(0, 6, 4)["label"] == labels.HARMS
    assert pair(0, 0, 10)["label"] == labels.NOT_DISTINGUISHED and pair(0, 0, 10)["p"] == 1.0
    ne = CellResult(labels.CELL_NOT_EVALUATED)
    r = labels.paired({1: OK, 2: OK}, {1: fail(1), 2: ne}, TH)
    assert r["pairs"] == 1 and r["d"] == 1


def test_false_negative_table_matches_the_adr() -> None:
    t = {row["p"]: row for row in labels.false_negative_table()}
    assert round(float(t[0.90]["one_series"]), 3) == 0.736 and round(float(t[0.90]["both_series"]), 3) == 0.542
    assert round(float(t[0.95]["both_series"]), 3) == 0.835 and round(float(t[0.97]["l_q_at_least_2"]), 2) == 0.81
    assert round(float(t[0.99]["l_q_at_least_2"]), 2) == 0.97


def _brute(q: dict[float, str], conf: dict[float, bool]) -> int:
    """The step of section 7 read straight off the table (loads 0.5, 1, 2, 4; one state per load)."""
    loads = [0.5, 1.0, 2.0, 4.0]
    if q[0.5] == NOT_EVALUABLE:
        return 1
    if q[0.5] == FAILS:
        return 2
    top = 0.5
    for ld in loads[1:]:
        if q[ld] != HOLDS:
            break
        top = ld
    if top >= 2:
        return 3
    nxt = loads[loads.index(top) + 1]
    if q[nxt] == NOT_EVALUABLE:
        return 4
    return 6 if conf[nxt] else 5


def test_every_series_state_combination_reaches_exactly_one_headline() -> None:
    """3^8 series states (two series at four loads, each HOLDS / FAILS / NOT EVALUABLE for Line Q) x 2^4 convergence statuses (one per load): 104,976 inputs, each one headline, agreeing with a brute-force reading."""
    loads = [0.5, 1.0, 2.0, 4.0]
    states = (HOLDS, FAILS, NOT_EVALUABLE)
    conv = {True: Convergence(labels.CONFIRMED, (), {}), False: Convergence(labels.NOT_CONFIRMED, (labels.RISING,), {})}
    template = {(a, g, q): type_state_from(a, g, q) for (a, g, q) in labels.COMBINATIONS}
    by_q = {q: next(ts for (a, g, qq), ts in template.items() if qq == q) for q in states}
    count = 0
    for assign in itertools.product(states, repeat=8):
        qs = {ld: (assign[2 * i], assign[2 * i + 1]) for i, ld in enumerate(loads)}
        combined = {ld: labels.combine_series(list(qs[ld]), "Q") for ld in loads}
        for cflags in itertools.product((True, False), repeat=4):
            conf = dict(zip(loads, cflags, strict=True))
            at = {ld: [SeriesAtLoad("M", by_q[qs[ld][0]], conv[conf[ld]], "m"), SeriesAtLoad("S", by_q[qs[ld][1]], conv[conf[ld]], "s")] for ld in loads}
            h = labels.decide(loads=at, th=TH)
            want = _brute(combined, conf)
            assert h.step == want and h.text
            count += 1
    assert count == 3**8 * 2**4


def type_state_from(a: str, g: str, q: str) -> TypeState:
    return TypeState(a, g, q, labels.COMBINATIONS[(a, g, q)])


def _loads(qs: dict[float, tuple[str, str]], confirmed: bool = True, ts_by_q: dict[str, TypeState] | None = None) -> dict[float, list[SeriesAtLoad]]:
    c = Convergence(labels.CONFIRMED if confirmed else labels.NOT_CONFIRMED, () if confirmed else (labels.NOT_SHOWN,), {})
    ts = ts_by_q or {HOLDS: type_state_from(HOLDS, HOLDS, HOLDS), FAILS: type_state_from(HOLDS, HOLDS, FAILS), NOT_EVALUABLE: type_state_from(NOT_EVALUABLE, NOT_EVALUABLE, NOT_EVALUABLE)}
    return {ld: [SeriesAtLoad("M", ts[a], c, "m"), SeriesAtLoad("S", ts[b], c, "s")] for ld, (a, b) in qs.items()}


H = (HOLDS, HOLDS)


def test_named_headlines() -> None:
    d = labels.decide
    assert d(loads=_loads({0.5: H, 1: H, 2: H, 4: H}), th=TH).text == "OVERLOAD-QUALIFIED UP TO 4; NO BREAK FOUND ON THE GRID"
    assert d(loads=_loads({0.5: H, 1: H, 2: H, 4: (FAILS, HOLDS)}), th=TH).text == "OVERLOAD-QUALIFIED UP TO 2; NOT QUALIFIED AT ℓ₁"
    assert d(loads=_loads({0.5: H, 1: H, 2: H, 4: (FAILS, HOLDS)}, confirmed=False), th=TH).text == "OVERLOAD-QUALIFIED UP TO 2; UNRESOLVED AT ℓ₁"
    ne = (NOT_EVALUABLE, HOLDS)
    assert d(loads=_loads({0.5: H, 1: H, 2: ne, 4: H}), th=TH).text == "OVERLOAD NOT EVALUABLE AT ℓ₁ — REFERENCE; ADDRESSING QUALIFIED UP TO 1"
    assert d(loads=_loads({0.5: H, 1: (FAILS, HOLDS), 2: H, 4: H}), th=TH).text.startswith("OVERLOAD NOT QUALIFIED AT ℓ₁; ADDRESSING QUALIFIED UP TO 0.5")
    assert d(loads=_loads({0.5: H, 1: (FAILS, HOLDS), 2: H, 4: H}, confirmed=False), th=TH).text.startswith("OVERLOAD UNRESOLVED AT ℓ₁ — CONVERGENCE NOT CONFIRMED (NOT SHOWN)")
    assert d(loads=_loads({0.5: H, 1: ne, 2: H, 4: H}), th=TH).text == "OVERLOAD NOT EVALUABLE AT ℓ₁ — REFERENCE; ADDRESSING QUALIFIED UP TO 0.5"
    assert d(loads=_loads({0.5: ne, 1: H, 2: H, 4: H}), th=TH).text == labels.HEAD_ANCHOR_NE
    assert d(loads=_loads({0.5: (FAILS, HOLDS), 1: H, 2: H, 4: H}), th=TH).text.startswith(labels.HEAD_ANCHOR_FAILS)
    assert d(loads=_loads({0.5: H}), missing_cells=3, th=TH).text == labels.HEAD_PAUSED
    assert d(loads=_loads({0.5: H}), paused=True, th=TH).text == labels.HEAD_PAUSED
    assert d(loads=_loads({0.5: H}), gate_failed=True, missing_cells=3, th=TH).text == labels.HEAD_ENGINEERING
    assert d(loads=_loads({0.5: H}), item_errors=True, gate_failed=True, th=TH).text == labels.HEAD_ITEM_ERRORS


def test_x8_handling() -> None:
    main = {0.5: H, 1: H, 2: H, 4: H}
    base = labels.decide(loads=_loads(main), th=TH)
    assert labels.x8_triggered(base.detail["L_Q"], TH, base.step)
    assert not labels.x8_triggered(2.0, TH, 3)
    withx8 = {**_loads(main), 8.0: [SeriesAtLoad("X", type_state_from(HOLDS, HOLDS, FAILS), Convergence(labels.CONFIRMED, (), {}), "x")]}
    paused = labels.decide(loads=withx8, x8_triggered=True, x8_status="PAUSED", th=TH)
    assert paused.text.endswith("NO BREAK FOUND ON THE GRID; LOAD 8 PAUSED") and paused.detail["L_Q"] == 4
    done = labels.decide(loads=withx8, x8_triggered=True, x8_status="COMPLETE", th=TH)
    assert done.text == "OVERLOAD-QUALIFIED UP TO 4; NOT QUALIFIED AT ℓ₁"
    assert labels.decide(loads=withx8, th=TH).detail["L_Q"] == 4  # X8 not triggered: load 8 never enters


def test_which_line_fails_and_hypotheses() -> None:
    flagged_a_holds = TypeState(HOLDS, NOT_EVALUABLE, FAILS, 3, True, True, False, 0, 0)
    assert labels.fails_print(flagged_a_holds) == "LINE A HOLDS; LINE G NOT EVALUABLE — REFERENCE; THE COMPOSITE FAILS ON LM CAPABILITY REDUCED / ADDRESS STABLE"
    assert labels.fails_print(TypeState(FAILS, NOT_EVALUABLE, FAILS, 4, True)) == "LINE A FAILS (LINE G NOT EVALUABLE — REFERENCE)"
    assert labels.fails_print(type_state_from(HOLDS, FAILS, FAILS)) == "LINE G FAILS (A HOLDS)"
    assert labels.fails_print(type_state_from(FAILS, NOT_READ, FAILS)) == "LINE A FAILS"
    assert labels.fails_print(type_state_from(HOLDS, HOLDS, FAILS)).startswith("NEITHER ALONE")
    g_fail = type_state_from(HOLDS, FAILS, FAILS)
    ts = {HOLDS: type_state_from(HOLDS, HOLDS, HOLDS), FAILS: g_fail, NOT_EVALUABLE: type_state_from(NOT_EVALUABLE, NOT_EVALUABLE, NOT_EVALUABLE)}
    h = labels.decide(loads=_loads({0.5: H, 1: (FAILS, HOLDS), 2: H, 4: H}, ts_by_q=ts), th=TH)
    hy = labels.hypotheses(h, {"M": g_fail}, labels.IMPROVES, HOLDS)
    assert hy == {"H23-A": "supported", "H23-O": "not supported", "H23-G": "supported", "H23-P": "supported"}
    assert labels.hypotheses(labels.Headline(0, labels.HEAD_PAUSED), {}, None, None)["H23-A"] == "not read"
    assert labels.licence(h) == [0.5]
    assert labels.licence(labels.Headline(2, "x")) == []


def test_regime_and_collapse_text() -> None:
    assert labels.reference_regime([0.95] * 3, TH) == labels.REGIME_NEAR
    assert labels.reference_regime([0.6, 0.7, 0.8], TH).startswith(labels.REGIME_DEGRADED)
    assert labels.collapse_free([False] * 9 + [True]) == "COLLAPSE-FREE: 9 of 10 counted cells never had a collapse onset"


@pytest.mark.parametrize("ct_name,floor", [("8K/16K", 0.90), ("2K/4K", 0.90), ("8K/8K", 0.50), ("2K/512", 0.50), ("8K/1K", 0.50)])
def test_floor_by_load(ct_name: str, floor: float) -> None:
    assert core.cell_type_by_name(ct_name).floor(TH) == floor
