# ruff: noqa: E501
"""P10IS1 verdicts, classes, labels and outcomes (ADR-0024 sections 8 and 9): pure functions of numbers, no I/O, no torch.

A *series* is ``{update: Pt(i, a_use)}`` for one cell, arm read, replicate and panel; DEP failures are given as the set of updates at which a qualified condition failed (the analysis computes them from counts with
``dep_failures``). The capacity step, the dense readings, the saturation pair, the efficiency step and the outcomes of C-CAPACITY, C-SATURATION and C-EFFICIENCY are written here from ADR-0024's text. Where ADR-0024 says a
rule is ADR-0021's and unchanged (the efficiency step verdicts, u_T, the saturation pair and arm classes), P10-S1's own audited functions are called, not copied (``studies.p10s1.classes``).

A condition that favours the store needs both panels in a replicate; a blocking condition needs either (ADR-0021 section 22 (h)); the denominator is always 5.
Status: implementation self-checked only. Not independent review, not Astra validation, not human approval.
"""

import math
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, NamedTuple

from . import core

EPS = 1e-12
PANELS = core.PANELS


def ge(a: float, b: float) -> bool:
    return a >= b - EPS


def le(a: float, b: float) -> bool:
    return a <= b + EPS


def lt(a: float, b: float) -> bool:
    return a < b - EPS


def gt(a: float, b: float) -> bool:
    return a > b + EPS


# --- status words -----------------------------------------------------------------------------------------------------------------------
NOT_EVALUATED, DEPENDENCE_FAILED, PANEL_DISAGREE = "NOT_EVALUATED", "DEPENDENCE_FAILED", "PANEL-DISAGREE"
CEILING, CAPACITY, GAIN_ONLY, REVERSED, BEHIND, NULL, FLAT_NOT_LOADED, UNRESOLVED = "CEILING", "CAPACITY", "GAIN WITHIN BUDGET ONLY", "REVERSED", "BEHIND WITHIN BUDGET", "NULL", "FLAT, NOT LOADED", "UNRESOLVED"
CAPACITY_STEP, GAIN_STEP, NOT_REPLICATED, NOT_LOADED, NO_GAIN, NOT_FULL_WITHIN_BUDGET, MIXED = "CAPACITY STEP", "GAIN WITHIN BUDGET", "NOT REPLICATED", "NOT LOADED", "NO GAIN", "NOT FULL WITHIN BUDGET", "MIXED"
CAPACITY_SUPPORTED, CAPACITY_ONE_TRANSITION, NOT_TESTED_BY_LOAD, CAPACITY_NOT_SUPPORTED, INTERMEDIATE = "CAPACITY_SUPPORTED", "CAPACITY_ONE_TRANSITION", "NOT_TESTED_BY_LOAD", "CAPACITY_NOT_SUPPORTED", "INTERMEDIATE"
CAPACITY_POSITIVE, CAPACITY_NEGATIVE, CAPACITY_NOT_TESTED, CAPACITY_INCONCLUSIVE = "CAPACITY-POSITIVE", "CAPACITY-NEGATIVE", "CAPACITY NOT TESTED", "CAPACITY-INCONCLUSIVE"
EFFICIENCY_POSITIVE, EFFICIENCY_NEGATIVE, EFFICIENCY_INCONCLUSIVE = "EFFICIENCY-POSITIVE", "EFFICIENCY-NEGATIVE", "EFFICIENCY-INCONCLUSIVE"
SAT_PROPORTIONAL, SAT_SUBPROPORTIONAL, SAT_NOT_MEASURED_OUTCOME, SAT_INCONCLUSIVE = "SATURATION-PROPORTIONAL", "SATURATION-SUBPROPORTIONAL", "SATURATION NOT MEASURED", "SATURATION-INCONCLUSIVE"
DENSE_AHEAD, DENSE_AHEAD_NOT_MC, STORE_NOT_BEHIND, DENSE_SPLIT_CELL = "DENSE AHEAD", "DENSE AHEAD (NOT AT MATCHED COMPUTE)", "STORE NOT BEHIND", "DENSE COMPARISON SPLIT"
ARM_DENSE_AHEAD, ARM_NOT_BEHIND, ARM_DENSE_SPLIT, ARM_NOT_APPLICABLE = "DENSE AHEAD", "NOT BEHIND DENSE", "DENSE SPLIT", "NOT APPLICABLE"
DENSE_HOLDS_MORE, STORE_HOLDS_MORE, SAME_AT_SATURATION, DENSE_STILL_RISING = "DENSE HOLDS MORE AT SATURATION", "STORE HOLDS MORE AT SATURATION", "SAME AT SATURATION", "DENSE STILL RISING"
DENSE_FASTER, DENSE_NOT_FASTER, DENSE_SPEED_UNDECIDED = "DENSE FASTER", "DENSE NOT FASTER", "DENSE SPEED UNDECIDED"
TREE_AHEAD, TREE_COMPETITIVE, TREE_BEHIND = "AHEAD", "COMPETITIVE", "BEHIND"
MC_SHORT, MC_AMBIGUOUS, OK = "MC-SHORT", "MC-AMBIGUOUS", "OK"
POST_HOC_ONLY = "POST-HOC READ ONLY; NO TRAINED ARM QUALIFIES"
MATCHED_COMPUTE_A_ONLY = "MATCHED COMPUTE IN MC-A ONLY"
MEASURED_COST_NOT_AVAILABLE = "MEASURED COST NOT AVAILABLE: a positive was not reachable"
KEY_LEARNING_LIMITED = "KEY-LEARNING-LIMITED"
UNDERTRAINED = "UNDERTRAINED-AT-U_P"
H8_NOT_CALIBRATED = "H8 NOT CALIBRATED AT U_P AT"


class Pt(NamedTuple):
    i: float
    a_use: float


Series = Mapping[int, Pt]


# --- DEP (section 8.1) ------------------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Obs:
    """Counts of one cell, snapshot and panel: ``n`` trained answer sites, ``correct`` (c), ``useful`` (u), ``disabled`` and ``shuffled`` correct counts, ``baseline`` the no-memory correct count on the same panel
    and fact set (b), the unseen-control counts."""

    n: int
    correct: int
    useful: int
    disabled: int | None = None
    shuffled: int | None = None
    baseline: int | None = None
    unseen_n: int = 0
    unseen_correct: int = 0

    @property
    def a_use(self) -> float:
        return self.useful / self.n if self.n else math.nan

    @property
    def i(self) -> float:
        return core.bits(self.useful, self.n)

    @property
    def leakage(self) -> bool:
        return self.unseen_n > 0 and not core.at_chance(self.unseen_correct, self.unseen_n)


DEP_CONDITIONS = ("a", "b", "c")


def dep_failures(obs: Obs, *, memory: bool, qualified: frozenset[str] | set[str] = frozenset(DEP_CONDITIONS), tail: float | None = None, floor: float | None = None, use_floor: float | None = None) -> set[str]:
    """The qualified DEP conditions that fail for a memory cell, snapshot and panel (section 8.1). DEP applies at a_use >= 0.25. DEP-a: memory disabled gives chance; DEP-b (memory arms only): value shuffle gives
    chance; DEP-c: fails only if BOTH c - u exceeds the upper 1 - 10^-4 quantile of Binomial(m, p+) and (c - u - m b/n)/n > 0.01. A count the condition needs and the record lacks is a failure (never a pass).
    A D-OQ cell (``memory`` False) is read by DEP-a and DEP-c only (ruling 17)."""
    t = core.Thresholds.from_config()
    c = core.cfg_of(None)["thresholds"]
    tail = float(c["dep_c_tail"]) if tail is None else tail
    floor = float(c["dep_c_floor"]) if floor is None else floor
    use_floor = t.dep_use_floor if use_floor is None else use_floor
    if obs.n <= 0 or lt(obs.a_use, use_floor):
        return set()
    failed: set[str] = set()
    if "a" in qualified and not (obs.disabled is not None and core.at_chance(obs.disabled, obs.n)):
        failed.add("a")
    if memory and "b" in qualified and not (obs.shuffled is not None and core.at_chance(obs.shuffled, obs.n)):
        failed.add("b")
    if "c" in qualified:
        if obs.baseline is None or core.dep_c_fails(obs.n, obs.correct, obs.useful, obs.baseline, tail=tail, floor=floor):
            failed.add("c")
    return failed


# --- fullness and the plateau (section 7.2) --------------------------------------------------------------------------------------------
def i_star(series: Series, limit: int) -> float:
    eligible = [p.i for u, p in series.items() if u <= limit]
    if not eligible:
        raise ValueError(f"no snapshot at or below {limit}")
    return max(eligible)


def plateau_ok(series: Series, u: int, th: core.Thresholds) -> bool:
    """i*(u) - i*(u/2) <= 0.10 and i*(u/2) >= 0.473 (a point test; the registered fullness of a cell that is not a ladder cell)."""
    if u not in series or u // 2 not in series:
        return False
    hi, half = i_star(series, u), i_star(series, u // 2)
    return le(hi - half, th.plateau_max) and ge(half, th.plateau_floor_i)


def full_at_u(series_by_panel: Mapping[str, Series], u: int, previous: int | None, th: core.Thresholds) -> bool:
    """Full at ladder point ``u`` on every panel: the plateau test at ``previous`` and at ``u`` (two consecutive ladder points of which ``u`` is the second). A first ladder point (no previous) is never full."""
    if previous is None:
        return False
    return all(plateau_ok(s, previous, th) and plateau_ok(s, u, th) for s in series_by_panel.values())


def point_full(series_by_panel: Mapping[str, Series], u: int, th: core.Thresholds) -> bool:
    """Fullness of a cell that is not a ladder cell at its run length: the plateau test at ``u`` on every panel."""
    return all(plateau_ok(s, u, th) for s in series_by_panel.values())


def first_full_length(series_by_panel: Mapping[str, Series], ladder: Sequence[int], th: core.Thresholds, upto: int) -> int | None:
    """An arm's own full length: the first ladder point <= ``upto`` at which it is full (two consecutive ladder points), read on snapshots up to ``upto``."""
    pts = [p for p in ladder if p <= upto]
    for k in range(1, len(pts)):
        if full_at_u(series_by_panel, pts[k], pts[k - 1], th):
            return pts[k]
    return None


def loaded_flag(series_by_panel: Mapping[str, Series], length: int | None, th: core.Thresholds) -> bool:
    """Loaded: full (at ``length``, None meaning not full) and i* <= 4.0 on every panel (section 7.2 item 8)."""
    return length is not None and all(le(i_star(s, length), th.loaded_i_max) for s in series_by_panel.values())


# --- matched compute (section 8.2) --------------------------------------------------------------------------------------------------
class McRead(NamedTuple):
    """One matched-compute reading of a pair (first, second): the update at which each is read, or the status MC-SHORT. ``ambiguous`` is MC-AMBIGUOUS (the two measures disagree on which cell costs more)."""

    status: str
    first_update: int | None
    second_update: int | None
    multiplier: float
    ambiguous: bool = False

    def ok(self) -> bool:
        return self.status == OK


def _direction(r: float) -> int:
    return 1 if r > 1.0 + EPS else (-1 if r < 1.0 - EPS else 0)


def _snapshot_at_least(mult: float, u_p: int, grid: Sequence[float]) -> int | None:
    if not math.isfinite(mult):
        return None
    for g in grid:
        if ge(g, mult):
            return core.multiple_of(u_p, g)
    return None


def mc_reading(cost_first: float, cost_second: float, *, u_p: int, run_first: int, run_second: int, grid: Sequence[float], mode: str, claim: str) -> McRead:
    """The matched-compute reading of a pair in ONE cost measure. ``first`` and ``second`` are the cells of the pair: in a capacity step (``mode`` 'capacity') first = the smaller cell N and second = the larger
    cell 4N (the cell whose advantage is claimed); in a dense reading (``mode`` 'dense') first = D-OQ and second = the arm (claimed). The costlier cell is read at U_P and the cheaper at the smallest grid snapshot
    whose cumulative cost is at least the costlier cell's at U_P; beyond the cheaper cell's run length, or above the grid, the pair is MC-SHORT. Equal costs: both at U_P.
    Capacity step, ruling 1: where the larger cell costs no more per update than the smaller, U_MC = U_P (the larger cell is never read later). ``claim`` is kept for the signature of the combined reading."""
    if mode not in ("capacity", "dense") or cost_first <= 0 or cost_second <= 0:
        raise ValueError("mc_reading: mode capacity/dense and positive costs")
    r = cost_second / cost_first  # claimed cell over the other
    d = _direction(r)
    if d <= 0 and mode == "capacity":
        return McRead(OK, u_p, u_p, 1.0)  # the larger cell costs no more: U_MC = U_P
    if d == 0:
        return McRead(OK, u_p, u_p, 1.0)
    mult = r if d > 0 else 1.0 / r
    if d > 0:  # the claimed (second) cell is costlier: read at U_P; the first at the matched snapshot
        u = _snapshot_at_least(mult, u_p, grid)
        if u is None or u > run_first:
            return McRead(MC_SHORT, None, u_p, mult)
        return McRead(OK, u, u_p, mult)
    u = _snapshot_at_least(mult, u_p, grid)  # dense mode: the first (D-OQ) is costlier at U_P; the claimed (arm) at the matched snapshot
    if u is None or u > run_second:
        return McRead(MC_SHORT, u_p, None, mult)
    return McRead(OK, u_p, u, mult)


def mc_combined(costs_a: tuple[float, float] | None, costs_t: tuple[float, float] | None, *, u_p: int, run_first: int, run_second: int, grid: Sequence[float], mode: str) -> dict[str, McRead | None]:
    """The three matched-compute readings of a pair (section 8.2): MC-A (analytic costs ``(first, second)`` per update), MC-T (measured; None where MC-T is not measured) and MC-C, which exists only where MC-T is
    measured. MC-C: (i) where the two measures agree on which cell costs more (an exactly equal measure agrees with the other), the reading whose multiplier is larger: the costlier cell at U_P, the cheaper at that
    reading's matched snapshot (in a capacity step the larger cell is always read at U_P: ruling 1); (ii) where they disagree (MC-AMBIGUOUS), the claimed cell (the larger cell of a capacity step, the arm of a
    dense reading) at U_P and the other at the smallest grid snapshot whose multiplier is at least the largest of r and 1/r over both measures."""
    out: dict[str, McRead | None] = {"MC-A": None, "MC-T": None, "MC-C": None}
    if costs_a is not None:
        out["MC-A"] = mc_reading(costs_a[0], costs_a[1], u_p=u_p, run_first=run_first, run_second=run_second, grid=grid, mode=mode, claim="second")
    if costs_t is not None:
        out["MC-T"] = mc_reading(costs_t[0], costs_t[1], u_p=u_p, run_first=run_first, run_second=run_second, grid=grid, mode=mode, claim="second")
    if costs_a is None or costs_t is None:
        return out
    ra, rt = costs_a[1] / costs_a[0], costs_t[1] / costs_t[0]
    da, dt = _direction(ra), _direction(rt)
    if da * dt < 0:  # MC-AMBIGUOUS
        mult = max(ra, 1.0 / ra, rt, 1.0 / rt)
        u = _snapshot_at_least(mult, u_p, grid)
        if u is None or u > run_first:
            out["MC-C"] = McRead(MC_SHORT, None, u_p, mult, True)
        else:
            out["MC-C"] = McRead(OK, u, u_p, mult, True)
        return out
    ma, mt = out["MC-A"], out["MC-T"]
    assert ma is not None and mt is not None
    # agree: the reading with the larger multiplier; where one of them is MC-SHORT the larger multiplier still decides (the entry carries its own status)
    out["MC-C"] = ma if ma.multiplier >= mt.multiplier else mt
    return out


# --- the capacity step, one replicate and panel (section 9.1) -------------------------------------------------------------------------
class StepResult(NamedTuple):
    verdict: str
    detail: dict[str, Any]


@dataclass(frozen=True)
class StepCtx:
    """What the verdict of one replicate and panel needs besides the two series: U_P, the cells' U_run, REF and LEAKAGE, the DEP failures of each cell (updates at which a qualified condition failed), whether each cell is
    full (``small_full`` / ``large_full``) and the smaller cell is loaded, the matched-compute readings (MC-T and MC-C absent where MC-T is not measured)."""

    u_p: int
    run_small: int
    run_large: int
    ref_ok: bool
    leakage: bool
    dep_failed_small: frozenset[int]
    dep_failed_large: frozenset[int]
    small_full: bool
    large_full: bool
    small_loaded: bool
    mc: Mapping[str, McRead | None]


def capacity_panel(small: Series, large: Series, ctx: StepCtx, th: core.Thresholds) -> StepResult:
    """One panel's verdict for the step N -> 4N (rows 1 to 10 of section 9.1, first match wins). DEPARTURE FROM P10-S1, by the lead's ruling: ADR-0024 section 9 says a BLOCKING condition needs only ONE panel, so a dependence
    failure on EITHER panel of either cell blocks the capacity step on BOTH panels (``ctx.dep_failed_*`` hold the failures of both panels; the analysis passes their union): the replicate is DEPENDENCE_FAILED, never PANEL-DISAGREE.
    P10-S1's code read DEP per panel (a failure on one panel gave PANEL-DISAGREE). This is the stricter reading for the store."""
    d: dict[str, Any] = {"mc": {k: (None if v is None else {"status": v.status, "small_update": (v.first_update), "large_update": v.second_update, "multiplier": v.multiplier, "ambiguous": v.ambiguous}) for k, v in ctx.mc.items()}}
    if not ctx.ref_ok or ctx.leakage:
        return StepResult(NOT_EVALUATED, {**d, "reason": "REF failed" if not ctx.ref_ok else "LEAKAGE"})
    if ctx.dep_failed_small or ctx.dep_failed_large:
        return StepResult(DEPENDENCE_FAILED, {**d, "dep_failed_small": sorted(ctx.dep_failed_small), "dep_failed_large": sorted(ctx.dep_failed_large)})
    u_p = ctx.u_p
    i_s_up, i_l_up = small[u_p].i, large[u_p].i
    i_s_run, i_s_half = i_star(small, ctx.run_small), i_star(small, ctx.run_small // 2)
    i_l_run = i_star(large, ctx.run_large)
    d_mu, d_sat, d_full = i_l_up - i_s_up, i_l_up - i_s_run, i_l_run - i_s_run
    d_mc: dict[str, float | None] = {}
    for name, read in ctx.mc.items():
        if read is None:
            continue
        d_mc[name] = (i_l_up - small[int(read.first_update)].i) if read.ok() and read.first_update is not None else None
    d.update(i_small_up=i_s_up, i_large_up=i_l_up, delta_mu=d_mu, delta_mc=d_mc, delta_sat=d_sat, delta_full=d_full, i_star_small_run=i_s_run, i_star_small_half=i_s_half, i_star_large_run=i_l_run, a_use_large_up=large[u_p].a_use)
    if ge(i_s_up, th.ceiling_i):
        return StepResult(CEILING, d)
    mc_ok = all(v is not None and ge(v, th.gain_min) for v in d_mc.values()) and "MC-A" in d_mc  # a pair MC-SHORT in any reading present fails this condition
    row4 = (
        ge(d_mu, th.gain_min) and mc_ok and ge(d_sat, th.gain_min) and ctx.small_loaded and ge(d_sat - 2.0 * (i_s_run - i_s_half), th.gain_min) and ge(large[u_p].a_use, th.a_use_floor_capacity)
    )  # fmt: skip
    if row4:
        return StepResult(CAPACITY, d)
    if ge(d_mu, th.gain_min):
        return StepResult(GAIN_ONLY, d)
    if le(d_mu, -th.gain_min) and le(d_full, -th.gain_min):
        return StepResult(REVERSED, d)
    if le(d_mu, -th.gain_min):
        return StepResult(BEHIND, d)
    if lt(abs(d_mu), th.null_max) and lt(abs(d_full), th.null_max) and ctx.small_full and ctx.large_full:
        return StepResult(NULL if ctx.small_loaded else FLAT_NOT_LOADED, d)
    return StepResult(UNRESOLVED, d)


def capacity_replicate(panels: Mapping[str, StepResult]) -> StepResult:
    """Both panels agree -> that verdict; otherwise PANEL-DISAGREE."""
    verdicts = {p: r.verdict for p, r in panels.items()}
    detail = {"panels": {p: {"verdict": r.verdict, **r.detail} for p, r in panels.items()}}
    if len(set(verdicts.values())) == 1:
        return StepResult(next(iter(verdicts.values())), detail)
    return StepResult(PANEL_DISAGREE, detail)


def capacity_step_class(verdicts: Sequence[str], small_not_full: Sequence[bool], th: core.Thresholds) -> str:
    """Step class over the five replicates (section 9.1, first match wins; the denominator is always 5)."""
    if len(verdicts) != th.replicates or len(small_not_full) != th.replicates:
        raise ValueError("a step class needs one verdict per replicate")
    c = Counter(verdicts)
    n = len(verdicts)
    if c[NOT_EVALUATED] >= th.not_evaluated_min:
        return NOT_EVALUATED
    if c[DEPENDENCE_FAILED] >= th.not_evaluated_min:
        return DEPENDENCE_FAILED
    if c[PANEL_DISAGREE] >= th.panel_disagree_min:
        return NOT_REPLICATED
    if c[CAPACITY] == n:
        return CAPACITY_STEP
    if c[CAPACITY] + c[GAIN_ONLY] == n:
        return GAIN_STEP
    if c[CEILING] + c[FLAT_NOT_LOADED] >= th.unloaded_min:
        return NOT_LOADED
    if c[REVERSED] >= th.paired_most:
        return REVERSED
    if c[NULL] + c[REVERSED] >= th.paired_most:
        return NO_GAIN
    if sum(1 for x in small_not_full if x) >= th.not_full_min:
        return NOT_FULL_WITHIN_BUDGET
    return MIXED


def capacity_arm_class(step_classes: Mapping[str, str], transitions: Mapping[str, Sequence[str]], a_use_largest_all5: bool) -> str:
    """Arm class (section 9.1, first match wins). ``a_use_largest_all5``: a_use >= 0.80 at 32K/16K at U_P in all 5 replicates (both panels)."""
    per = {t: [step_classes[s] for s in steps] for t, steps in transitions.items()}
    if any(all(c == NOT_EVALUATED for c in cs) for cs in per.values()):
        return NOT_EVALUATED
    if any(c == DEPENDENCE_FAILED for c in step_classes.values()):
        return DEPENDENCE_FAILED
    has_step = {t: any(c == CAPACITY_STEP for c in cs) for t, cs in per.items()}
    if all(has_step.values()) and not any(c == REVERSED for c in step_classes.values()) and a_use_largest_all5:
        return CAPACITY_SUPPORTED
    if any(has_step.values()):
        return CAPACITY_ONE_TRANSITION
    if any(all(c in (NOT_LOADED, NOT_FULL_WITHIN_BUDGET) for c in cs) for cs in per.values()):
        return NOT_TESTED_BY_LOAD
    if all(any(c in (NO_GAIN, REVERSED) for c in cs) for cs in per.values()) and not any(has_step.values()):
        return CAPACITY_NOT_SUPPORTED
    return INTERMEDIATE


# --- the dense comparison (section 9.2) -------------------------------------------------------------------------------------------------
READINGS = ("MU", "MC-A", "MC-T", "MC-C", "D-BEST")
MATCHED_COMPUTE_READINGS = ("MC-A", "MC-T", "MC-C")


class DenseRep(NamedTuple):
    """One replicate of one arm at the larger cell of one of its CAPACITY STEPs: ``d[reading][panel]`` = i(arm) - i(D-OQ) (None where the reading is not available: MC-SHORT, MC-T not measured), ``status[reading]``
    OK / MC-SHORT / NOT MEASURED, ``blocked[reading]``: D-OQ failed a qualified DEP condition at a snapshot that reading reads (a store-favouring label is not established there; a dense lead still stands)."""

    d: Mapping[str, Mapping[str, float | None]]
    status: Mapping[str, str]
    blocked: Mapping[str, bool]


def dense_cell_label(reps: Sequence[DenseRep], th: core.Thresholds, *, mct_measured: bool) -> dict[str, Any]:
    """Cell label (section 9.2): DENSE AHEAD if d <= -0.25 on either panel in >= 4 replicates in at least one reading (MU, MC-A, MC-T where measured, MC-C, D-BEST); printed DENSE AHEAD (NOT AT MATCHED COMPUTE) where the
    lead holds in MU or D-BEST only. STORE NOT BEHIND if d > -0.25 on both panels in all 5 replicates in every reading (MC-A, MC-T, MU, D-BEST and MC-C), MC-T measured, no matched-compute pair MC-SHORT, no
    D-OQ DEP block. DENSE COMPARISON SPLIT otherwise."""
    readings = [r for r in READINGS if mct_measured or r not in ("MC-T", "MC-C")]
    counts: dict[str, int] = {}
    for r in readings:
        counts[r] = sum(1 for rep in reps if rep.status.get(r) == OK and any(v is not None and le(v, th.dense_ahead_bits) for v in rep.d[r].values()))
    ahead_in = [r for r in readings if counts[r] >= th.paired_most]
    out: dict[str, Any] = {"counts": counts, "readings": readings, "ahead_in": ahead_in}
    if ahead_in:
        mc_hit = any(r in MATCHED_COMPUTE_READINGS for r in ahead_in)
        out["label"] = DENSE_AHEAD if mc_hit else DENSE_AHEAD_NOT_MC
        return out
    complete = mct_measured and len(reps) == th.replicates
    clear = complete and all(
        rep.status.get(r) == OK and not rep.blocked.get(r, False) and all(v is not None and gt(v, th.dense_ahead_bits) for v in rep.d[r].values()) for rep in reps for r in readings
    )  # fmt: skip
    out["label"] = STORE_NOT_BEHIND if clear else DENSE_SPLIT_CELL
    out["reason"] = "" if clear else ("MC-T not measured" if not mct_measured else "a reading is not clear of -0.25 in all 5, is MC-SHORT, or D-OQ's DEP is blocked")
    return out


def is_dense_ahead(label: str) -> bool:
    return label in (DENSE_AHEAD, DENSE_AHEAD_NOT_MC)


class SatDenseRep(NamedTuple):
    """A replicate at a loaded cell: the arm and D-OQ, each at its own full length. ``d_sat[panel]`` = i*(arm) - i*(D-OQ), ``ratio[panel]`` = I_use ratio (None for a zero denominator), ``dense_full`` whether D-OQ
    is full at the cell, ``cost_ok`` D-OQ's cost per update is at least the arm's in both cost measures (False where MC-T is not measured), ``blocked`` D-OQ failed a qualified DEP condition at a snapshot read."""

    d_sat: Mapping[str, float]
    ratio: Mapping[str, float | None]
    dense_full: bool
    cost_ok: bool
    blocked: bool


def dense_at_saturation(reps: Sequence[SatDenseRep], th: core.Thresholds, *, mct_measured: bool) -> dict[str, Any]:
    """Dense at saturation for one loaded cell (section 9.2): DENSE HOLDS MORE (d_sat <= -0.25 in >= 4 replicates, a replicate counting if EITHER panel satisfies it); STORE HOLDS MORE (I_use ratio >= 1.10 on both panels
    in all 5, D-OQ full, D-OQ's cost per update at least the arm's in both cost measures, no D-OQ DEP block); SAME AT SATURATION otherwise, with DENSE STILL RISING if D-OQ is not full."""
    ahead = sum(1 for r in reps if any(le(v, th.dense_ahead_bits) for v in r.d_sat.values()))
    if ahead >= th.paired_most:
        return {"label": DENSE_HOLDS_MORE, "sublabels": [], "replicates_ahead": ahead}
    ratio_ok = len(reps) == th.replicates and all(v is None or ge(v, th.beats_dense_ratio) for r in reps for v in r.ratio.values())
    full_ok = len(reps) == th.replicates and all(r.dense_full for r in reps)
    cost_ok = mct_measured and all(r.cost_ok for r in reps)
    unblocked = all(not r.blocked for r in reps)
    if ratio_ok and full_ok and cost_ok and unblocked:
        return {"label": STORE_HOLDS_MORE, "sublabels": [], "replicates_ahead": ahead}
    sub = [DENSE_STILL_RISING] if not full_ok else []
    return {"label": SAME_AT_SATURATION, "sublabels": sub, "replicates_ahead": ahead, "failing": [n for n, ok in (("ratio", ratio_ok), ("dense full", full_ok), ("cost", cost_ok), ("D-OQ DEP", unblocked)) if not ok]}


def dense_arm_label(cell_labels: Mapping[str, str], sat_labels: Mapping[str, str], th: core.Thresholds) -> str:
    """Arm-level combination across cells (section 9.2). ``cell_labels``: the dense label of the larger cell of each CAPACITY STEP of the arm (empty: NOT APPLICABLE); ``sat_labels``: the dense-at-saturation label
    of each loaded cell. DENSE AHEAD if DENSE AHEAD at any such cell or DENSE HOLDS MORE at any loaded cell; NOT BEHIND DENSE if STORE NOT BEHIND at every such cell and DENSE HOLDS MORE at no loaded cell; DENSE SPLIT otherwise."""
    if not cell_labels:
        return ARM_NOT_APPLICABLE
    if any(is_dense_ahead(v) for v in cell_labels.values()) or any(v == DENSE_HOLDS_MORE for v in sat_labels.values()):
        return ARM_DENSE_AHEAD
    if all(v == STORE_NOT_BEHIND for v in cell_labels.values()) and not any(v == DENSE_HOLDS_MORE for v in sat_labels.values()):
        return ARM_NOT_BEHIND
    return ARM_DENSE_SPLIT


# --- the saturation pair (section 9.4) -------------------------------------------------------------------------------------------------
def saturation_bits(facts: int, series: Series, length: int) -> float:
    """S(N) = F x i*(cell at its full length) bits."""
    return facts * i_star(series, length)


def saturation_pair(small: Mapping[str, Any], large: Mapping[str, Any], *, ref_ok: bool, leakage: bool, th: core.Thresholds) -> StepResult:
    """Pair verdict for one replicate (section 9.4, first match wins). ``small`` and ``large``: ``{"facts", "slots", "series": {panel: Series}, "length": {panel-independent own full length or U_run}, "loaded": bool, "dep_failed": bool}``."""
    from studies.p10s1 import classes as c1

    d: dict[str, Any] = {}
    for tag, side in (("small", small), ("large", large)):
        ser = side["series"]
        length = int(side["length"])
        d[tag] = {
            "slots": side["slots"], "facts": side["facts"], "length": length, "loaded": bool(side["loaded"]),
            "b_bits_per_slot": {p: saturation_bits(side["facts"], ser[p], length) / side["slots"] for p in PANELS},
            "last_doubling_gain": {p: i_star(ser[p], length) - i_star(ser[p], length // 2) for p in PANELS},
        }  # fmt: skip
    if not ref_ok or leakage:
        return StepResult(c1.NOT_EVALUATED, {**d, "reason": "REF failed" if not ref_ok else "LEAKAGE"})
    if small["dep_failed"] or large["dep_failed"]:
        return StepResult(c1.DEPENDENCE_FAILED, d)
    if not (small["loaded"] and large["loaded"]):
        return StepResult(c1.NOT_FULL, d)
    rho = {p: saturation_bits(large["facts"], large["series"][p], int(large["length"])) / saturation_bits(small["facts"], small["series"][p], int(small["length"])) for p in PANELS}
    d["rho"] = rho
    if all(ge(r, th.saturation_ratio) for r in rho.values()):
        return StepResult(c1.PROPORTIONAL, d)
    return StepResult(c1.SUBPROPORTIONAL, d)


def saturation_outcome(arm_classes: Mapping[str, str], *, sat256_absent: bool) -> dict[str, Any]:
    """C-SATURATION outcome (ADR-0021 section 8.10 as ADR-0024 section 9.4 keeps it): SATURATION-PROPORTIONAL if F-OQ, T-OQ or F-OQ-IVF is SATURATION_PROPORTIONAL_ALL_PAIRS (H8 alone cannot give it);
    SATURATION-SUBPROPORTIONAL if F-OQ and T-OQ are both SATURATION_DOES_NOT_SCALE; SATURATION NOT MEASURED if both are SATURATION_NOT_MEASURED; SATURATION-INCONCLUSIVE otherwise, with the reason."""
    from studies.p10s1 import classes as c1

    proportional = [a for a in ("F-OQ", "T-OQ", "F-OQ-IVF") if arm_classes.get(a) == c1.SAT_PROPORTIONAL_ALL_PAIRS]
    notes = ["256 NOT MEASURED — NOT FULL WITHIN CEILING"] if sat256_absent else []
    if proportional:
        return {"label": SAT_PROPORTIONAL, "arms": proportional, "notes": notes, "reasons": []}
    foq, toq = arm_classes.get("F-OQ"), arm_classes.get("T-OQ")
    if foq == c1.SAT_DOES_NOT_SCALE and toq == c1.SAT_DOES_NOT_SCALE:
        return {"label": SAT_SUBPROPORTIONAL, "arms": ["F-OQ", "T-OQ"], "notes": notes, "reasons": ["F-OQ and T-OQ are both SATURATION_DOES_NOT_SCALE"]}
    if foq == c1.SAT_NOT_MEASURED and toq == c1.SAT_NOT_MEASURED:
        return {"label": SAT_NOT_MEASURED_OUTCOME, "arms": [], "notes": notes, "reasons": ["F-OQ and T-OQ are both SATURATION_NOT_MEASURED"]}
    reasons = [f"{a}: {arm_classes.get(a, 'none')}" for a in ("F-OQ", "T-OQ")]
    if any(arm_classes.get(a) == c1.DEPENDENCE_FAILED for a in ("F-OQ", "T-OQ", "F-OQ-IVF", "H8")):
        reasons.append("DEPENDENCE_FAILED")
    return {"label": SAT_INCONCLUSIVE, "arms": [], "notes": notes, "reasons": reasons}


# --- the efficiency line (section 9.5) ----------------------------------------------------------------------------------------------
class UView:
    """The part of P10-S1's ``View`` that ``classes.u_t`` reads (``updates``, ``run``, ``i``, ``dep``), over a series and the updates at which a qualified DEP condition failed."""

    def __init__(self, series: Series, run: int, dep_failed: frozenset[int] | set[int]) -> None:
        self.series, self.run, self._dep = dict(series), run, frozenset(dep_failed)
        self.updates = tuple(sorted(self.series))

    def i(self, u: int) -> float:
        return self.series[u].i

    def dep(self, u: int) -> bool | None:
        if u in self._dep:
            return False
        return True


def u_t_of(series_by_panel: Mapping[str, Series], run: int, dep_failed: Mapping[str, frozenset[int]]) -> Any:
    from studies.p10s1 import classes as c1

    return c1.u_t([UView(series_by_panel[p], run, dep_failed.get(p, frozenset())) for p in PANELS])


def u_t_panel(series: Series, run: int, dep_failed: frozenset[int]) -> Any:
    """One u_T per panel (a blocking label counts either panel)."""
    from studies.p10s1 import classes as c1

    return c1.u_t([UView(series, run, dep_failed)]).ut


def efficiency_step(small: Any, large: Any, *, ref_ok: bool, leakage: bool, run_small: int, run_large: int, cost_small: float, cost_large: float) -> Any:
    """ADR-0021 section 8.8's step verdict (P10-S1's ``classes.efficiency_step``) in ONE cost reading: the costs per update of that reading stand in for both of its measures."""
    from studies.p10s1 import classes as c1

    return c1.efficiency_step(small, large, ref_ok=ref_ok, leakage=leakage, run_small=run_small, run_large=run_large, cost_small={"cpu": cost_small, "madds": cost_small}, cost_large={"cpu": cost_large, "madds": cost_large})


def dense_speed(arm_ut: Sequence[Sequence[Any]], dense_ut: Sequence[Sequence[Any] | None], cost_arm: float, cost_dense: float, th: core.Thresholds, *, blocked: Sequence[bool] | None = None) -> str:
    """Dense speed at the larger cell of a FASTER STEP, in ONE cost reading (section 9.5): DENSE FASTER if D-OQ's c_T is at most 0.8 of the arm's in >= 4 replicates (a replicate counts if EITHER panel satisfies it, for
    every value the censoring bounds allow); DENSE NOT FASTER if it is above 0.8 in all 5 replicates on both panels for every value the bounds allow (a replicate whose D-OQ DEP failed does not establish it);
    DENSE SPEED UNDECIDED otherwise. ``arm_ut[replicate][panel]`` and ``dense_ut`` are P10-S1's ``UT``."""
    f = th.dense_faster_cost
    if len(arm_ut) != th.replicates:
        return DENSE_SPEED_UNDECIDED
    blocked = list(blocked) if blocked is not None else [False] * len(arm_ut)

    def sure(a: Any, d: Any) -> bool:
        return le(d.hi * cost_dense, f * a.lo * cost_arm)

    def possible(a: Any, d: Any) -> bool:
        return le(d.lo * cost_dense, f * a.hi * cost_arm)

    pairs_ = [(list(zip(a, d, strict=True)) if d is not None else None) for a, d in zip(arm_ut, dense_ut, strict=True)]
    if sum(1 for rep in pairs_ if rep is not None and any(sure(a, d) for a, d in rep)) >= th.paired_most:
        return DENSE_FASTER
    if all(rep is not None and not any(possible(a, d) for a, d in rep) and not blocked[k] for k, rep in enumerate(pairs_)):
        return DENSE_NOT_FASTER
    return DENSE_SPEED_UNDECIDED


def efficiency_outcome(arm_classes: Mapping[str, Mapping[str, str]], dense: Mapping[str, Mapping[str, Sequence[str]]], *, mct_measured: bool) -> dict[str, Any]:
    """C-EFFICIENCY rows 3 to 5 (section 9.5). ``arm_classes[reading][arm]`` with readings E-A and E-T (E-T only where MC-T is measured); ``dense[reading][arm]`` the list of dense-speed labels, one per FASTER-STEP cell
    of that arm in that reading. EFFICIENCY-POSITIVE: F-OQ or T-OQ is EFFICIENCY_SUPPORTED in both E-A and E-T and DENSE NOT FASTER at every FASTER-STEP cell in both readings. EFFICIENCY-NEGATIVE: F-OQ and T-OQ are
    both EFFICIENCY_NOT_SUPPORTED in E-A, or both in E-T; or at least one is EFFICIENCY_SUPPORTED in both readings and every such arm is DENSE FASTER at one or more FASTER-STEP cells in one or more readings.
    EFFICIENCY-INCONCLUSIVE otherwise."""
    readings = ["E-A"] + (["E-T"] if mct_measured else [])
    sup = "EFFICIENCY_SUPPORTED"
    # row 4 (b) is evaluated over the readings that EXIST (ADR-0024 sections 9.5 and 10: with MC-T NOT MEASURED a negative stays reachable through E-A: "no negative becomes unreachable"); the positive needs both readings
    supported_all = [a for a in core.EFFICIENCY_ARMS if all(arm_classes[r].get(a) == sup for r in readings)]
    positive = [a for a in supported_all if mct_measured and all(x == DENSE_NOT_FASTER for r in readings for x in dense[r].get(a, [])) and all(len(dense[r].get(a, [])) > 0 for r in readings)]
    if positive:
        return {"label": EFFICIENCY_POSITIVE, "arms": positive, "reasons": [], "e_a_only": False}
    both_not = {r: all(arm_classes[r].get(a) == "EFFICIENCY_NOT_SUPPORTED" for a in core.EFFICIENCY_ARMS) for r in readings}
    if any(both_not.values()):
        return {"label": EFFICIENCY_NEGATIVE, "arms": [], "reasons": [f"F-OQ and T-OQ are both EFFICIENCY_NOT_SUPPORTED in {r}" for r, v in both_not.items() if v], "e_a_only": not mct_measured}
    if supported_all and all(any(x == DENSE_FASTER for r in readings for x in dense[r].get(a, [])) for a in supported_all):
        return {"label": EFFICIENCY_NEGATIVE, "arms": supported_all, "reasons": ["every EFFICIENCY_SUPPORTED arm is DENSE FASTER at one or more FASTER-STEP cells in one or more readings"], "e_a_only": not mct_measured}
    reasons = [f"{r}: " + ", ".join(f"{a}: {arm_classes[r].get(a, 'none')}" for a in core.EFFICIENCY_ARMS) for r in readings]
    if any(x == DENSE_SPEED_UNDECIDED for r in readings for a in core.EFFICIENCY_ARMS for x in dense[r].get(a, [])):
        reasons.append(DENSE_SPEED_UNDECIDED)
    if len({tuple(arm_classes[r].get(a) for a in core.EFFICIENCY_ARMS) for r in readings}) > 1:
        reasons.append("READINGS DISAGREE")
    if not mct_measured:
        reasons.append("MEASURED COST NOT AVAILABLE")
    return {"label": EFFICIENCY_INCONCLUSIVE, "arms": [], "reasons": reasons, "e_a_only": not mct_measured}


# --- descriptive: sparse arms (section 9.6) ---------------------------------------------------------------------------------------------
def sparse_label(ratios: Sequence[Mapping[str, Mapping[str, float]]], th: core.Thresholds) -> str:
    """T-OQ against F-OQ-IVF on I_use at 8K/4K and 32K/16K: ``ratios[replicate][cell][panel]``. AHEAD if the ratio is >= 1.03 on both panels in >= 4 replicates at both cells; COMPETITIVE if >= 0.97; otherwise BEHIND."""
    cells = sorted({c for rep in ratios for c in rep})

    def count(threshold: float, cell: str) -> int:
        return sum(1 for rep in ratios if cell in rep and all(ge(rep[cell][p], threshold) for p in PANELS))

    if cells and all(count(th.tree_ahead_ratio, c) >= th.paired_most for c in cells):
        return TREE_AHEAD
    if cells and all(count(th.tree_competitive_ratio, c) >= th.paired_most for c in cells):
        return TREE_COMPETITIVE
    return TREE_BEHIND


# --- H8 annotations and KEY-LEARNING-LIMITED (section 4) ---------------------------------------------------------------------------
def key_learning_limited(h8_class: str, foq_class: str) -> bool:
    """KEY-LEARNING-LIMITED if H8 is CAPACITY_SUPPORTED and F-OQ is not. A printed label; it enters no outcome."""
    return h8_class == CAPACITY_SUPPORTED and foq_class != CAPACITY_SUPPORTED


def h8_annotations(undertrained: Sequence[str], calibrated: Sequence[str], cells: Sequence[str]) -> dict[str, str]:
    """UNDERTRAINED-AT-U_P at a calibrated cell where H8's calibration a_use was below 0.90 at U_P on either draw or panel; ``H8 NOT CALIBRATED AT U_P AT <cell>`` at a cell where H8 was not calibrated. Annotations gate nothing."""
    out: dict[str, str] = {}
    for name in cells:
        if name not in calibrated:
            out[name] = f"{H8_NOT_CALIBRATED} {name}"
        elif name in undertrained:
            out[name] = UNDERTRAINED
    return out


# --- the capacity outcome (section 9.3) ----------------------------------------------------------------------------------------------------
class ArmCapacity(NamedTuple):
    arm: str
    cls: str
    dense: str  # the arm-level dense label (DENSE AHEAD, NOT BEHIND DENSE, DENSE SPLIT, NOT APPLICABLE)


def capacity_outcome(arms: Mapping[str, ArmCapacity], *, every_step_unloaded_or_unfull: bool, mct_measured: bool) -> dict[str, Any]:
    """Rows 3 to 6 of section 9.3 (rows 1 and 2 are the analysis's status). CAPACITY-POSITIVE: F-OQ, T-OQ or F-OQ-IVF is CAPACITY_SUPPORTED and NOT BEHIND DENSE (a positive carried by F-OQ-IVF alone is POST-HOC READ ONLY;
    NO TRAINED ARM QUALIFIES). CAPACITY-NEGATIVE: (a) F-OQ and T-OQ are both CAPACITY_NOT_SUPPORTED, or (b) at least one of the three is CAPACITY_SUPPORTED and every such arm is DENSE AHEAD. CAPACITY NOT TESTED: for F-OQ
    and T-OQ every step is NOT LOADED or NOT FULL WITHIN BUDGET. CAPACITY-INCONCLUSIVE otherwise."""
    learned = [arms[a] for a in core.DECISION_ARMS if a in arms]
    supported = [a for a in learned if a.cls == CAPACITY_SUPPORTED]
    positive = [a for a in supported if a.dense == ARM_NOT_BEHIND]
    out: dict[str, Any] = {"mct_note": None if mct_measured else MEASURED_COST_NOT_AVAILABLE}
    if positive:
        trained = [a for a in positive if a.arm in core.TRAINED_ENTRY_ARMS]
        out.update(label=CAPACITY_POSITIVE, row=3, arms=[a.arm for a in positive], reasons=[], post_hoc_only=not trained)
        return out
    foq, toq = arms.get("F-OQ"), arms.get("T-OQ")
    if foq is not None and toq is not None and foq.cls == CAPACITY_NOT_SUPPORTED and toq.cls == CAPACITY_NOT_SUPPORTED:
        out.update(label=CAPACITY_NEGATIVE, row=4, clause="(a)", arms=["F-OQ", "T-OQ"], reasons=["(a) F-OQ and T-OQ are both CAPACITY_NOT_SUPPORTED"], post_hoc_only=False)
        return out
    if supported and all(a.dense == ARM_DENSE_AHEAD for a in supported):
        out.update(label=CAPACITY_NEGATIVE, row=4, clause="(b)", arms=[a.arm for a in supported], reasons=["(b) every CAPACITY_SUPPORTED arm is DENSE AHEAD"], post_hoc_only=False)
        return out
    if every_step_unloaded_or_unfull:
        out.update(label=CAPACITY_NOT_TESTED, row=5, arms=[], reasons=["for F-OQ and T-OQ every step is NOT LOADED or NOT FULL WITHIN BUDGET"], post_hoc_only=False)
        return out
    reasons = [f"{a.arm}: {a.cls}; dense {a.dense}" for a in learned]
    out.update(label=CAPACITY_INCONCLUSIVE, row=6, arms=[], reasons=reasons, post_hoc_only=False)
    return out


# --- tags (section 1): every positive label carries the standing tag -------------------------------------------------------------------
POSITIVE_LABELS = (
    CAPACITY_STEP, CAPACITY_SUPPORTED, CAPACITY_POSITIVE, "EFFICIENCY_SUPPORTED", EFFICIENCY_POSITIVE, STORE_NOT_BEHIND, ARM_NOT_BEHIND, STORE_HOLDS_MORE, SAT_PROPORTIONAL, "PROPORTIONAL STEP",
    "SATURATION_PROPORTIONAL_ALL_PAIRS", "CAPACITY_ONE_TRANSITION", "FASTER STEP",
)  # fmt: skip
_POSITIVE_RE = re.compile(r"(?<![\w-])(?<!DENSE )(?<!NOT )(" + "|".join(re.escape(p) for p in sorted(POSITIVE_LABELS, key=len, reverse=True)) + r")(?:S)?(?![\w-])")
_TAGGED_SPAN = re.compile(r"\[" + re.escape(core.STANDING_TAG) + r"[^\]]*\]")


def tagged(label: str, *details: str) -> str:
    """``label [STORE ONLY; ORACLE-ADDRESSED; RECALL OF TRAINED RANDOM FACTS; DICT DOMINATES ON THIS TASK; detail; ...]``."""
    return f"{label} [{'; '.join([core.STANDING_TAG, *[d for d in details if d]])}]"


_QUOTED_SPAN = re.compile(r"`[^`]*`")


def _covered(text: str) -> list[tuple[int, int]]:
    """Spans that need no tag: a bracket headed by the standing tag (it covers what it lists) and a back-quoted span (a label named as a thing that cannot be reached, not claimed)."""
    return [(m.start(), m.end()) for rx in (_TAGGED_SPAN, _QUOTED_SPAN) for m in rx.finditer(text)]


def untagged_positive_labels(text: str) -> list[str]:
    spans = _covered(text)
    tag_after = re.compile(r"(?:\s*\([^)]*\))?\s*\[" + re.escape(core.STANDING_TAG))
    return [m.group(1) for m in _POSITIVE_RE.finditer(text) if not tag_after.match(text, m.end()) and not any(a <= m.start() < b for a, b in spans)]


def tag_positives(text: str) -> str:
    """Free text with ``[<standing tag>]`` appended after every positive label that has none (labels in a tagged bracket or between back-quotes are left as they are)."""
    out: list[str] = []
    last = 0
    spans = _covered(text)
    tag_after = re.compile(r"(?:\s*\([^)]*\))?\s*\[" + re.escape(core.STANDING_TAG))
    for m in _POSITIVE_RE.finditer(text):
        if tag_after.match(text, m.end()) or any(a <= m.start() < b for a, b in spans):
            continue
        out.append(text[last : m.end()] + f" [{core.STANDING_TAG}]")
        last = m.end()
    return "".join(out) + text[last:]


def emit(text: str) -> str:
    """The one way label text reaches a report: raises ValueError if a positive label has no standing tag."""
    bad = untagged_positive_labels(text)
    if bad:
        raise ValueError(f"positive label(s) without the standing tag: {sorted(set(bad))}")
    return text


def is_positive(label: str) -> bool:
    return bool(_POSITIVE_RE.search(label))


def printable(label: str, *details: str) -> str:
    return emit(tagged(label, *details)) if is_positive(label) else label
