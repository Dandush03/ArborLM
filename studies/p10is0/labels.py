# ruff: noqa: E501
"""P10IS0 labels (ADR-0023 sections 5.3, 6, 7): pure functions from measurements to cell results, arm class, the three lines per series, the combination of series into a load, the break points, the
convergence check on registered draws, the paired comparison, the false-negative table and the decision procedure (steps 0 to 6). Nothing here reads a file, trains or evaluates a model.

Readings fixed here where the ADR is silent (each listed in the implementer's report):
* a learned cell that diverged is FAILED on every condition and is not LM-flagged (the ADR says only "FAILED on every condition");
* step 0 order when several apply: item errors, then a failed gate, then PAUSED;
* ``m`` values are exact fractions of integer counts (ruling 1), so no float tie arises at 0.01 or 0.02.
"""

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any

from .core import Thresholds, median

HOLDS, FAILS, NOT_EVALUABLE, NOT_READ = "HOLDS", "FAILS", "NOT EVALUABLE", "NOT READ"
SUCCEEDED, FAILED, CELL_NOT_EVALUATED = "SUCCEEDED", "FAILED", "NOT_EVALUATED"
RELIABLE, UNRELIABLE, CLASS_FAILS, CLASS_NOT_EVALUATED = "RELIABLE", "UNRELIABLE", "FAILS", "NOT_EVALUATED"
A_CONDITIONS, G_CONDITION = (1, 2, 3, 5, 6), 4
ALL_CONDITIONS = (1, 2, 3, 4, 5, 6)
FLAGGABLE_REMOVING = (2, 3, 5, 6)

REGIME_NEAR, REGIME_DEGRADED = "REFERENCE NEAR CEILING", "REFERENCE DEGRADED"
CONFIRMED, NOT_CONFIRMED = "CONVERGENCE CONFIRMED", "CONVERGENCE NOT CONFIRMED"
RISING, DECLINING, NOT_SHOWN = "RISING", "DECLINING AT T", "NOT SHOWN"
IMPROVES, HARMS, NOT_DISTINGUISHED = "IMPROVES ON A0", "HARMS", "NOT DISTINGUISHED"
NOT_SHOWN_REFUSED = "CONVERGENCE NOT SHOWN — EXTENSION REFUSED (BUDGET)"
NOT_SHOWN_REHEARSAL = "CONVERGENCE NOT SHOWN IN REHEARSAL"
NON_FINITE_REHEARSAL = "NON-FINITE IN REHEARSAL"
FLAT_BELOW_FLOOR = "A5-D FLAT BELOW FLOOR"

HEAD_PAUSED = "INCOMPLETE — PAUSED"
HEAD_ENGINEERING = "ENGINEERING_FAIL / INCOMPLETE"
HEAD_ITEM_ERRORS = "ENGINEERING STOP — ITEM ERRORS"
HEAD_ANCHOR_NE = "NOT EVALUABLE — ANCHOR REFERENCE"
HEAD_ANCHOR_FAILS = "ANCHOR NOT REPRODUCED AT THE CONVERGED DURATION"
FIXED_SENTENCES = (
    "W7 is told the record length. The memory is told the answer position. Synthetic fixed-length records; one frozen 27,392-parameter backbone. A5-D was chosen for P10-S0 after its P9-II result was observed. "
    "μ = 1.0 was calibrated at 0.5 facts per slot."
)


# --- observations (integer counts) -------------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Obs:
    """One readout of one cell. Panels are (correct, n) integer counts; the rest are the eval record's fields as P10-S0's ``observation_from_eval`` reads them."""

    a: tuple[int, int]
    b: tuple[int, int]
    h1: tuple[int, int]
    h2: tuple[int, int]
    dep_chance_a: bool = True
    dep_chance_b: bool = True
    leakage: bool = False
    distinct_top1: int = 0
    largest_share: float = 1.0
    probe_facts: int = 0
    lm_rise: float = math.nan
    address_stability: float = math.nan
    a_use_a: float = math.nan
    a_use_b: float = math.nan

    @staticmethod
    def _acc(p: tuple[int, int]) -> float:
        return p[0] / p[1] if p[1] else math.nan

    @property
    def acc_a(self) -> float:
        return self._acc(self.a)

    @property
    def acc_b(self) -> float:
        return self._acc(self.b)

    @property
    def acc_h1(self) -> float:
        return self._acc(self.h1)

    @property
    def acc_h2(self) -> float:
        return self._acc(self.h2)

    @property
    def m_p(self) -> Fraction:
        """m_P = (correct_A + correct_B) / (n_A + n_B) (ruling 1)."""
        return Fraction(self.a[0] + self.b[0], self.a[1] + self.b[1])

    @property
    def m_h(self) -> Fraction:
        return Fraction(self.h1[0] + self.h2[0], self.h1[1] + self.h2[1])


def _at_least(value: float, bound: float) -> bool:
    return math.isfinite(value) and value >= bound


@dataclass(frozen=True)
class CellResult:
    status: str
    failed: frozenset[int] = frozenset()
    lm_flagged: bool = False
    nonfinite_update: int | None = None


def reference_usable(ref: Obs | None, floor: float) -> bool:
    """Evaluability of a draw at a cell type: A6 at or above the floor on both panels (ruling 2); a NaN is not usable."""
    return ref is not None and _at_least(ref.acc_a, floor) and _at_least(ref.acc_b, floor)


def conditions_failed(obs: Obs, ref: Obs, th: Thresholds, *, include_condition_1: bool = True) -> frozenset[int]:
    """The conditions of section 6.2 that do not hold (P10-S0's ``cell_verdict`` formulas with this study's config thresholds)."""
    from studies.p9ii import classes as p9c

    failed: set[int] = set()
    if include_condition_1 and not (_at_least(obs.acc_a, th.success_fraction_of_a6 * ref.acc_a) and _at_least(obs.acc_b, th.success_fraction_of_a6 * ref.acc_b)):
        failed.add(1)
    if not (obs.dep_chance_a and obs.dep_chance_b):
        failed.add(2)
    if not p9c.slot_condition(obs.distinct_top1, obs.largest_share, obs.probe_facts):
        failed.add(3)
    h = th.heldout_fraction
    if not all(_at_least(hv, h * av) for hv in (obs.acc_h1, obs.acc_h2) for av in (obs.acc_a, obs.acc_b)):
        failed.add(4)
    if obs.leakage:
        failed.add(5)
    if not (_at_least(obs.a_use_a, th.dependence_fraction * obs.acc_a) and _at_least(obs.a_use_b, th.dependence_fraction * obs.acc_b)):
        failed.add(6)
    return frozenset(failed)


def cell_result(obs: Obs | None, ref: Obs | None, floor: float, th: Thresholds, *, nonfinite_update: int | None = None, a6_nonfinite: bool = False) -> CellResult:
    """NOT_EVALUATED when A6 is missing, non-finite or below its floor on the draw; a diverged learned cell is FAILED on every condition (NON-FINITE AT UPDATE u); otherwise SUCCEEDED or FAILED with the numbers."""
    from studies.p9ii import classes as p9c

    if a6_nonfinite or not reference_usable(ref, floor):
        return CellResult(CELL_NOT_EVALUATED)
    if nonfinite_update is not None:
        return CellResult(FAILED, frozenset(ALL_CONDITIONS), False, nonfinite_update)
    assert obs is not None and ref is not None
    failed = conditions_failed(obs, ref, th)
    return CellResult(FAILED if failed else SUCCEEDED, failed, p9c.lm_flagged(obs.lm_rise, ref.lm_rise))


# --- class of an arm at a cell type (section 6.3) ---------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class ArmClass:
    cls: str
    evaluated: int
    successes: int
    failures: int
    ne_draws: int
    lm_reduced: bool
    n_a: int
    n_g: int
    condition_failures: Mapping[int, int] = field(default_factory=dict)


def arm_class(results: Mapping[int, CellResult], th: Thresholds, lm_flagged_cells: int | None = None) -> ArmClass:
    """First match wins: NOT_EVALUATED (more than one draw NOT_EVALUATED); RELIABLE (at most one failed cell among the evaluated cells and no LM CAPABILITY REDUCED); UNRELIABLE (at least 3 successes); FAILS."""
    if lm_flagged_cells is None:
        from studies.p9ii import core as p9iicore

        lm_flagged_cells = int(p9iicore.LM_FLAGGED_CELLS)
    ev = {d: r for d, r in results.items() if r.status != CELL_NOT_EVALUATED}
    ne = len(results) - len(ev)
    successes = sum(1 for r in ev.values() if r.status == SUCCEEDED)
    failures = len(ev) - successes
    reduced = sum(1 for r in ev.values() if r.lm_flagged) > lm_flagged_cells
    n_a = sum(1 for r in ev.values() if r.failed & set(A_CONDITIONS))
    n_g = sum(1 for r in ev.values() if not (r.failed & set(A_CONDITIONS)) and G_CONDITION in r.failed)
    counts = {c: sum(1 for r in ev.values() if c in r.failed) for c in ALL_CONDITIONS}
    if ne > th.max_not_evaluated_draws:
        cls = CLASS_NOT_EVALUATED
    elif failures <= th.max_failed_reliable and not reduced:
        cls = RELIABLE
    elif successes >= th.min_successes:
        cls = UNRELIABLE
    else:
        cls = CLASS_FAILS
    return ArmClass(cls, len(ev), successes, failures, ne, reduced, n_a, n_g, counts)


def address_stable(values: Sequence[float | None], th: Thresholds) -> bool:
    """The median over evaluated cells of the share of facts with the same top-1 slot on Panels A and B is at least 0.80; a non-finite value counts as 0 (ruling 8; P10-S0's rule)."""
    clean = [0.0 if v is None or not math.isfinite(v) else float(v) for v in values]
    return bool(clean) and median(clean) >= th.stable_threshold


# --- the lines at a cell type (section 6.4) --------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class RefFlags:
    """Stage R's reference flags at a cell type: condition 4 alone keeps the cell type (Line G NOT EVALUABLE); any of 2, 3, 5, 6 removes it."""

    cond4: bool = False
    other: tuple[int, ...] = ()

    @property
    def removed(self) -> bool:
        return bool(self.other)


@dataclass(frozen=True)
class TypeState:
    a: str
    g: str
    q: str
    combination: int
    flagged_cond4: bool = False
    lm_reduced: bool = False
    address_stable: bool | None = None
    n_a: int | None = None
    n_g: int | None = None


COMBINATIONS: dict[tuple[str, str, str], int] = {
    (NOT_EVALUABLE, NOT_EVALUABLE, NOT_EVALUABLE): 1,
    (HOLDS, NOT_EVALUABLE, NOT_EVALUABLE): 2,
    (HOLDS, NOT_EVALUABLE, FAILS): 3,
    (FAILS, NOT_EVALUABLE, FAILS): 4,
    (HOLDS, HOLDS, HOLDS): 5,
    (HOLDS, HOLDS, FAILS): 6,
    (HOLDS, FAILS, FAILS): 7,
    (FAILS, NOT_READ, FAILS): 8,
}  # the eight combinations of section 6.4's totality table


def type_state(cls: ArmClass | None, flags: RefFlags, stable: bool | None, th: Thresholds) -> TypeState:
    """Section 6.4, first match wins. ``cls`` None means the cell type has no results because it was removed or NOT RUN."""
    if flags.removed or cls is None or cls.cls == CLASS_NOT_EVALUATED:
        return TypeState(NOT_EVALUABLE, NOT_EVALUABLE, NOT_EVALUABLE, 1)
    n_a, n_g = cls.n_a, cls.n_g
    a = HOLDS if n_a < th.line_fail_cells else FAILS
    ok_stable = bool(stable)
    if flags.cond4:
        q = FAILS if (n_a >= th.line_fail_cells or cls.lm_reduced or not ok_stable) else NOT_EVALUABLE
        g = NOT_EVALUABLE
        return TypeState(a, g, q, COMBINATIONS[(a, g, q)], True, cls.lm_reduced, ok_stable, n_a, n_g)
    g = NOT_READ if a == FAILS else (HOLDS if n_g < th.line_fail_cells else FAILS)
    q = HOLDS if (cls.cls == RELIABLE and ok_stable) else FAILS
    return TypeState(a, g, q, COMBINATIONS[(a, g, q)], False, cls.lm_reduced, ok_stable, n_a, n_g)


# --- loads and break points (section 6.6) ---------------------------------------------------------------------------------------------------------
def combine_series(states: Sequence[str], line: str) -> str:
    """Both hold -> HOLDS; either FAILS -> FAILS (for Line G, NOT READ counts as FAILS); otherwise NOT EVALUABLE. One series (X8) gives its own state."""
    mapped = [FAILS if (line == "G" and s == NOT_READ) else s for s in states]
    if mapped and all(s == HOLDS for s in mapped):
        return HOLDS
    if any(s == FAILS for s in mapped):
        return FAILS
    return NOT_EVALUABLE


@dataclass(frozen=True)
class Break:
    line: str
    l: float | None  # noqa: E741 - the ADR's L
    l1: float | None
    l1_state: str | None
    non_monotone: bool


def break_point(load_states: Mapping[float, str], line: str = "Q") -> Break:
    """L = the largest grid load at which the line HOLDS and at every lower grid load (None if not at 0.5); l1 = the next grid load above L (the lowest when L is None); no l1 when L is the highest load run;
    a HOLDS above l1 adds NON-MONOTONE and does not raise L."""
    loads = sorted(load_states)
    level: float | None = None
    for ld in loads:
        if load_states[ld] == HOLDS:
            level = ld
        else:
            break
    if level is None:
        l1: float | None = loads[0] if loads else None
    else:
        above = [x for x in loads if x > level]
        l1 = above[0] if above else None
    non_monotone = l1 is not None and any(load_states[x] == HOLDS for x in loads if x > l1)
    return Break(line, level, l1, load_states[l1] if l1 is not None else None, non_monotone)


# --- convergence (sections 5.1, 5.3) -------------------------------------------------------------------------------------------------------------
def plateau_step_ok(m_values: Sequence[Fraction], th: Thresholds) -> bool:
    """Two consecutive steps m(2e)-m(e) and m(4e)-m(2e), each at most the step in absolute value. ``m_values`` = [m(e), m(2e), m(4e)]."""
    if len(m_values) != th.plateau_steps_required + 1:
        raise ValueError("a plateau needs m at e, 2e and 4e")
    limit = Fraction(str(th.plateau_step))
    return all(abs(m_values[i + 1] - m_values[i]) <= limit for i in range(th.plateau_steps_required))


@dataclass(frozen=True)
class Convergence:
    status: str
    tags: tuple[str, ...]
    d: Mapping[str, Fraction | None]


def convergence_check(shown: bool, deltas: Mapping[str, Sequence[Fraction]], th: Thresholds) -> Convergence:
    """Section 5.3 with ruling 5: d = the median over the cells with a record of m(T) - m(T/2) for each (arm, measure) key. CONFIRMED if SHOWN in rehearsal and every |d| <= 0.02; otherwise NOT CONFIRMED with every
    tag that applies: RISING (some d > 0.02), DECLINING AT T (some d < -0.02), NOT SHOWN."""
    limit = Fraction(str(th.confirm_step))
    d = {k: (median(list(v)) if v else None) for k, v in deltas.items()}
    tags: list[str] = []
    if any(x is not None and x > limit for x in d.values()):
        tags.append(RISING)
    if any(x is not None and x < -limit for x in d.values()):
        tags.append(DECLINING)
    if not shown:
        tags.append(NOT_SHOWN)
    if not tags and any(x is None for x in d.values()):
        tags.append(NOT_SHOWN)  # no cells with a record to confirm on: confirmation is not possible
    return Convergence(CONFIRMED if not tags else NOT_CONFIRMED, tuple(tags), d)


def load_convergence(series_q: Mapping[str, str], series_conv: Mapping[str, Convergence]) -> tuple[str, tuple[str, ...]]:
    """CONFIRMED if every series whose Line Q state at the load is FAILS is CONVERGENCE CONFIRMED; otherwise NOT CONFIRMED (with the union of the tags)."""
    bad = [series_conv[s] for s, q in series_q.items() if q == FAILS and series_conv[s].status != CONFIRMED]
    tags = tuple(dict.fromkeys(t for c in bad for t in c.tags))
    return (NOT_CONFIRMED if bad else CONFIRMED), tags


# --- annotations (section 6.7) ---------------------------------------------------------------------------------------------------------------------
def sign_test_p(b: int, c: int) -> Fraction:
    """Exact two-sided sign test on b and c discordant pairs; p = 1 with none (ruling 15)."""
    n = b + c
    if n == 0:
        return Fraction(1)
    tail = sum(math.comb(n, k) for k in range(0, min(b, c) + 1))
    return min(Fraction(1), Fraction(2 * tail, 2**n))


def paired(a5d: Mapping[int, CellResult], a0: Mapping[int, CellResult], th: Thresholds) -> dict[str, Any]:
    """A5-D against A0 in series M: d = (A5-D succeeds, A0 fails) - (the reverse) over the pairs on draws that are evaluated; IMPROVES if d >= 6 and p < 0.05; HARMS if d <= -6 and p < 0.05."""
    b = c = used = 0
    for d in sorted(set(a5d) & set(a0)):
        x, y = a5d[d], a0[d]
        if CELL_NOT_EVALUATED in (x.status, y.status):
            continue
        used += 1
        b += int(x.status == SUCCEEDED and y.status == FAILED)
        c += int(x.status == FAILED and y.status == SUCCEEDED)
    p = sign_test_p(b, c)
    dd = b - c
    label = IMPROVES if (dd >= th.paired_d and p < Fraction(str(th.paired_p))) else HARMS if (dd <= -th.paired_d and p < Fraction(str(th.paired_p))) else NOT_DISTINGUISHED
    return {"d": dd, "a5d_only": b, "a0_only": c, "pairs": used, "p": float(p), "label": label}


def reference_regime(a6_mean_panel_accuracies: Sequence[float], th: Thresholds) -> str:
    """Section 6.5, from the median over draws of A6's mean panel accuracy: NEAR CEILING (>= 0.90) or DEGRADED (A6 = x)."""
    vals = [x for x in a6_mean_panel_accuracies if math.isfinite(x)]
    if not vals:
        return "REFERENCE NOT MEASURED"
    m = median(vals)
    if m >= th.reference_near_ceiling:
        return REGIME_NEAR
    if m < th.a6_floor_loaded:
        return f"{REGIME_DEGRADED} (A6 = {m:.4f}; BELOW THE 0.50 FLOOR)"
    return f"{REGIME_DEGRADED} (A6 = {m:.4f})"


def false_negative_table(ps: Sequence[float] = (0.90, 0.95, 0.97, 0.99)) -> list[dict[str, float | str]]:
    """ANALYTICAL (not measured): with per-cell success probability p and independent cells, P(RELIABLE in one series) = P(Bin(10, p) >= 9), in both series its square, and Line Q holding at loads 0.5, 1 and 2 about the cube
    of that (loads share draws, so approximate). A printed descriptive; it enters no label."""
    out = []
    for p in ps:
        one = p**10 + 10 * p**9 * (1 - p)
        out.append({"kind": "ANALYTICAL", "p": p, "one_series": one, "both_series": one**2, "l_q_at_least_2": one**6})
    return out


def per_draw_bound(k: int, n: int) -> float | None:
    """The one-sided 95% Clopper-Pearson lower bound on the per-draw success probability (section 6.3), by P9-II's function; None with no evaluated draw."""
    if n <= 0:
        return None
    from studies.p9ii import classes as p9c

    return float(p9c.clopper_pearson_lower(k, n, 0.05))


def collapse_free(onsets: Sequence[bool]) -> str:
    n = len(onsets)
    return f"COLLAPSE-FREE: {sum(1 for x in onsets if not x)} of {n} counted cells never had a collapse onset"


# --- the decision procedure (section 7) ------------------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class SeriesAtLoad:
    series: str
    state: TypeState
    convergence: Convergence
    cell_type: str
    removed_note: str | None = None


@dataclass
class Headline:
    step: int
    text: str
    detail: dict[str, Any] = field(default_factory=dict)


def fails_print(ts: TypeState) -> str:
    """Which line fails at l1, for one series whose Line Q FAILS (section 7)."""
    if ts.flagged_cond4:
        if ts.a == FAILS:
            return "LINE A FAILS (LINE G NOT EVALUABLE — REFERENCE)"
        why = [w for w, on in (("LM CAPABILITY REDUCED", ts.lm_reduced), ("ADDRESS STABLE", ts.address_stable is False)) if on]
        return "LINE A HOLDS; LINE G NOT EVALUABLE — REFERENCE; THE COMPOSITE FAILS ON " + " / ".join(why)
    if ts.a == FAILS:
        return "LINE A FAILS"
    if ts.g == FAILS:
        return "LINE G FAILS (A HOLDS)"
    return "NEITHER ALONE (both hold, the composite or ADDRESS STABLE does not)"


def decide(
    *,
    loads: Mapping[float, Sequence[SeriesAtLoad]],
    x8_triggered: bool = False,
    x8_status: str | None = None,
    missing_cells: int = 0,
    gate_failed: bool = False,
    item_errors: bool = False,
    paused: bool = False,
    th: Thresholds | None = None,
) -> Headline:
    """Steps 0 to 6 of section 7, applied in order; exactly one headline results. ``loads`` maps each grid load to its series' states (two series for the main grid, one for X8). ``x8_status`` is None, "COMPLETE", "PAUSED"
    or "INCOMPLETE" when X8 was triggered. Load 8 enters the break point only when X8 is COMPLETE."""
    if item_errors:
        return Headline(0, HEAD_ITEM_ERRORS)
    if gate_failed:
        return Headline(0, HEAD_ENGINEERING)
    if missing_cells or paused:
        return Headline(0, HEAD_PAUSED, {"missing_cells": missing_cells})
    use = {ld: v for ld, v in loads.items() if not (ld == 8.0 and not (x8_triggered and x8_status == "COMPLETE"))}
    qstate = {ld: combine_series([s.state.q for s in v], "Q") for ld, v in use.items()}
    brk = break_point(qstate, "Q")
    lowest = min(use)
    tag = ""
    if x8_triggered and x8_status in ("PAUSED", "INCOMPLETE"):
        tag = f"; LOAD 8 {x8_status}"
    detail: dict[str, Any] = {"q_by_load": qstate, "L_Q": brk.l, "l1": brk.l1, "l1_state": brk.l1_state, "non_monotone": brk.non_monotone}
    if qstate[lowest] == NOT_EVALUABLE:
        return Headline(1, HEAD_ANCHOR_NE, detail)
    if qstate[lowest] == FAILS:
        status, tags = load_convergence({s.series: s.state.q for s in use[lowest]}, {s.series: s.convergence for s in use[lowest]})
        return Headline(2, f"{HEAD_ANCHOR_FAILS} ({status})", {**detail, "convergence": status, "tags": tags})
    assert brk.l is not None
    if brk.l >= 2:
        if brk.l1 is None:
            end = "NO BREAK FOUND ON THE GRID"
        elif brk.l1_state == NOT_EVALUABLE:
            end = "NOT EVALUABLE AT ℓ₁ — REFERENCE"
        else:
            conv, tags = load_convergence({s.series: s.state.q for s in use[brk.l1]}, {s.series: s.convergence for s in use[brk.l1]})
            end = "UNRESOLVED AT ℓ₁" if conv == NOT_CONFIRMED else "NOT QUALIFIED AT ℓ₁"
            detail["convergence"], detail["tags"] = conv, tags
        return Headline(3, f"OVERLOAD-QUALIFIED UP TO {brk.l:g}; {end}{tag}", detail)
    assert brk.l1 is not None
    if brk.l1_state == NOT_EVALUABLE:
        return Headline(4, f"OVERLOAD NOT EVALUABLE AT ℓ₁ — REFERENCE; ADDRESSING QUALIFIED UP TO {brk.l:g}{tag}", detail)
    conv, tags = load_convergence({s.series: s.state.q for s in use[brk.l1]}, {s.series: s.convergence for s in use[brk.l1]})
    detail.update({"convergence": conv, "tags": tags, "which_line": {s.series: fails_print(s.state) for s in use[brk.l1] if s.state.q == FAILS}})
    if conv == NOT_CONFIRMED:
        return Headline(5, f"OVERLOAD UNRESOLVED AT ℓ₁ — CONVERGENCE NOT CONFIRMED ({' / '.join(tags)}); ADDRESSING QUALIFIED UP TO {brk.l:g}{tag}", detail)
    return Headline(6, f"OVERLOAD NOT QUALIFIED AT ℓ₁; ADDRESSING QUALIFIED UP TO {brk.l:g}{tag}", detail)


def x8_triggered(main_l_q: float | None, th: Thresholds, headline_step: int) -> bool:
    """Section 8: X8 runs only if L_Q = 4 after the complete main grid (step 3 reached); nothing else is passed to the launcher."""
    return headline_step == 3 and main_l_q is not None and main_l_q == th.x8_trigger_load


def hypotheses(h: Headline, lines_at_l1: Mapping[str, TypeState], a5d_vs_a0_at_load_2: str | None, q_at_half: str | None) -> dict[str, str]:
    """H23-A, H23-O, H23-G, H23-P. A reading is not a success of the science. Not read when the procedure ended at step 0."""
    if h.step == 0:
        return dict.fromkeys(("H23-A", "H23-O", "H23-G", "H23-P"), "not read")
    out = {"H23-A": "supported" if q_at_half == HOLDS else "not supported"}
    lq = h.detail.get("L_Q")
    out["H23-O"] = "supported" if (lq is not None and lq >= 2 and h.step == 3) else "not supported"
    l1_state = h.detail.get("l1_state")
    if h.step == 1 or h.detail.get("l1") is None or l1_state == NOT_EVALUABLE:  # R11: at step 2 l1 = 0.5 exists and FAILS, so it is read
        out["H23-G"] = "not read"
    else:
        prints = [fails_print(ts) for ts in lines_at_l1.values() if ts.q == FAILS]
        out["H23-G"] = "supported" if prints and all(p == "LINE G FAILS (A HOLDS)" for p in prints) else "not supported"
    out["H23-P"] = "not read" if a5d_vs_a0_at_load_2 is None else ("supported" if a5d_vs_a0_at_load_2 == IMPROVES else "not supported")
    return out


def licence(h: Headline) -> list[float]:
    """Section 15 items 1 and 2: the lane licence depends on L_Q only: none for steps 0 to 2; loads up to L_Q (tested cell types) otherwise, whatever the status of l1."""
    if h.step < 3:
        return []
    lq = h.detail.get("L_Q")
    return [] if lq is None else [ld for ld in (0.5, 1.0, 2.0, 4.0, 8.0) if ld <= lq]
