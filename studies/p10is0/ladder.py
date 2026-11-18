# ruff: noqa: E501
"""P10IS0 convergence ladder (ADR-0023 sections 5.1, 5.2, 9): the plateau rule, e*, T = 2 e*, A5-D FLAT BELOW FLOOR, the six-part extension rule with the budget B, the per-condition reference flags, the events before the freeze, Stage R's own cap
and the worker count of the memory rule. Pure functions over curves of integer-count accuracies; no file, no model. All decisions are made by code (section 5.2 (vi)).

``durations.json`` (``durations_record``) is the only product that leaves Stage R in clear: per cell type e*, T, SHOWN or NOT SHOWN, FLAT BELOW FLOOR, extension granted or refused, and the reference flags.
"""

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any

from . import core, labels
from .core import CellType, Thresholds

STATUS_UNDECIDED, STATUS_SHOWN, STATUS_CANDIDATE, STATUS_CEILING, STATUS_NONFINITE, STATUS_REFUSED = "UNDECIDED", "SHOWN", "CANDIDATE", "NOT_SHOWN_AT_CEILING", "NON_FINITE", "REFUSED"
RUN_KEYS = (("A5-D", 1), ("A5-D", 2), ("A6", 1), ("A6", 2))  # the four runs of a cell type: arm and calibration draw


class EngineeringStop(RuntimeError):
    """A case the rules do not cover, or a worker count below one: an engineering stop until the human lead rules; never a label."""


@dataclass(frozen=True)
class Point:
    """m_P and m_H at one ladder exposure, exact fractions of integer counts (ruling 1)."""

    m_p: Fraction
    m_h: Fraction


@dataclass
class Curve:
    arm: str
    draw: int
    points: dict[int, Point] = field(default_factory=dict)
    nonfinite_update: int | None = None


def candidate_es(ceiling: int, ladder: Sequence[int], th: Thresholds) -> list[int]:
    """Ladder values e for which m at e, 2e, 4e lies on the ladder up to ``ceiling`` (base ceiling 16,384: e up to 4,096; extended 32,768: e up to 8,192)."""
    return [e for e in ladder if e * 2**th.plateau_steps_required <= ceiling]


@dataclass(frozen=True)
class Decision:
    status: str
    e_star: int | None = None
    t: int | None = None
    shown: bool = False
    flat_below_floor: bool = False
    label: str | None = None
    reason: str = ""


def decide_cell_type(curves: Mapping[tuple[str, int], Curve], floor: float, ceiling: int, th: Thresholds, ladder: Sequence[int], *, cfg: Mapping[str, Any] | None = None) -> Decision:
    """The ladder's decision for one cell type from the four runs' curves reached so far (the round barrier: every run has the point before it is read, ruling 11).

    * any non-finite run: NON_FINITE (T = base ceiling T; not an extension candidate);
    * the smallest e with the two-sided plateau on both measures for A5-D and A6 on both calibration draws, and A6's m_P(e) at least the floor on both draws: SHOWN, T = 2 e*; A5-D FLAT BELOW FLOOR where A5-D's m_P(e*) is below
      the floor on either draw;
    * no plateau and the ceiling reached: CANDIDATE (base ceiling) or NOT_SHOWN_AT_CEILING (extended ceiling, T = extended T);
    * otherwise UNDECIDED (train the next doubling).
    """
    c = cfg or core.load_config()
    base_t, ext_t = int(c["ladder"]["base_ceiling_t"]), int(c["ladder"]["extended_ceiling_t"])
    if set(curves) != set(RUN_KEYS):
        raise ValueError("a cell type has exactly four runs (A5-D and A6 on calibration draws 1 and 2)")
    if any(cv.nonfinite_update is not None for cv in curves.values()):
        return Decision(STATUS_NONFINITE, None, base_t, False, False, labels.NON_FINITE_REHEARSAL, "a run's trainer raised a non-finite check")
    reached = min(max(cv.points, default=0) for cv in curves.values())
    floor_f = Fraction(str(floor))
    step = th.plateau_steps_required
    for e in candidate_es(ceiling, ladder, th):
        needed = [e * 2**i for i in range(step + 1)]
        if needed[-1] > reached:
            break
        if any(x not in cv.points for cv in curves.values() for x in needed):
            raise ValueError(f"a run lacks a point of the ladder at {needed}")
        flat = all(labels.plateau_step_ok([cv.points[x].m_p for x in needed], th) and labels.plateau_step_ok([cv.points[x].m_h for x in needed], th) for cv in curves.values())
        ref_ok = all(curves[("A6", d)].points[e].m_p >= floor_f for d in (1, 2))
        if flat and ref_ok:
            below = any(curves[("A5-D", d)].points[e].m_p < floor_f for d in (1, 2))
            return Decision(STATUS_SHOWN, e, th.t_factor * e, True, below, labels.FLAT_BELOW_FLOOR if below else None)
    if reached >= ceiling:
        if ceiling > max(int(x) for x in c["ladder"]["base"]):
            return Decision(STATUS_CEILING, None, ext_t, False, False, labels.NOT_SHOWN_REHEARSAL, "no plateau at the extended ceiling")
        return Decision(STATUS_CANDIDATE, None, base_t, False, False, None, "no plateau on the base ladder: an extension candidate")
    return Decision(STATUS_UNDECIDED)


# --- costs and the extension rule (section 5.1 items 1 to 6) -------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Rates:
    """Stage 3's quiet rates: seconds per update and seconds per evaluation by (arm, slots)."""

    sec_per_update: Mapping[tuple[str, int], float]
    eval_seconds: Mapping[tuple[str, int], float]

    def train(self, arm: str, slots: int, updates: int) -> float:
        return self.sec_per_update[(arm, slots)] * updates

    def evaluate(self, arm: str, slots: int, n: int = 1) -> float:
        return self.eval_seconds[(arm, slots)] * n


@dataclass(frozen=True)
class Stage:
    name: str
    total_seconds: float
    longest_seconds: float


def _stage(name: str, tasks: Sequence[float]) -> Stage:
    return Stage(name, float(sum(tasks)), float(max(tasks, default=0.0)))


def main_grid_stage(cts: Sequence[CellType], t_assumed: Mapping[str, int], rates: Rates, draws: int = 10) -> Stage:
    """Training at each cell type's T (stage 3's seconds per update) with three evaluations per cell."""
    tasks = [rates.train(arm, ct.slots, ct.updates(t_assumed[ct.name])) + rates.evaluate(arm, ct.slots, 3) for ct in cts for arm in ct.arms for _ in range(draws)]
    return _stage("main", tasks)


def extension_round_stage(ct: CellType, rates: Rates, ladder_top: int) -> Stage:
    """One extension round: the four runs go from the base ceiling to twice it (A5-D and A6, two calibration draws), with one evaluation each."""
    tasks = [rates.train(arm, ct.slots, ct.updates(ladder_top)) + rates.evaluate(arm, ct.slots) for arm in ("A5-D", "A6") for _ in (1, 2)]
    return _stage(f"extension:{ct.name}", tasks)


def calibration_stage(ct: CellType, t_exposures: int, rates: Rates, n_points: int = 7) -> Stage:
    """X8's calibration: four runs to 2T exposures with an evaluation at each ladder point."""
    tasks = [rates.train(arm, ct.slots, ct.updates(2 * t_exposures)) + rates.evaluate(arm, ct.slots, n_points) for arm in ("A5-D", "A6") for _ in (1, 2)]
    return _stage(f"calibration:{ct.name}", tasks)


def projected_hours(
    *,
    cts: Sequence[CellType],
    t_assumed: Mapping[str, int],
    granted_rounds: Sequence[str],
    rates: Rates,
    charged_hours: float,
    other_hours: float,
    x8: CellType | None,
    workers: int,
    ladder_top: int,
    x8_t: int,
    draws: int = 10,
) -> tuple[float, list[Stage]]:
    """P (item 2), in charged hours at 1x: hours already charged + measured gates, generation, analysis and report + the summed worker-seconds of the main grid at each cell type's T, of the extension rounds granted so
    far and the one under decision, and of X8 and its calibration at T = ``x8_t`` (if kept), divided by the workers, + the longest single task of each stage. Every stage is a list entry, so the longest of each is added."""
    by_name = {ct.name: ct for ct in cts}
    stages = [main_grid_stage(cts, t_assumed, rates, draws)]
    stages += [extension_round_stage(by_name[n], rates, ladder_top) for n in granted_rounds]
    if x8 is not None:
        stages += [calibration_stage(x8, x8_t, rates), main_grid_stage([x8], {x8.name: x8_t}, rates, draws)]
    work = sum(s.total_seconds for s in stages) / workers
    longest = sum(s.longest_seconds for s in stages)
    return charged_hours + other_hours + (work + longest) / 3600.0, stages


@dataclass(frozen=True)
class ExtensionDecision:
    cell_type: str
    granted: bool
    projected_hours: float
    budget_hours: float


def decide_extensions(
    candidates: Sequence[CellType],
    *,
    cts: Sequence[CellType],
    t_known: Mapping[str, int],
    rates: Rates,
    charged_hours: float,
    other_hours: float,
    x8: CellType | None,
    th: Thresholds | None = None,
    cfg: Mapping[str, Any] | None = None,
) -> list[ExtensionDecision]:
    """Section 5.1 items 1 to 6. Decided once, after every cell type's base ladder has finished. Candidates are taken in order of ascending load, series M before S at equal load; each is granted if P with it is at most B, refused
    otherwise, and after a refusal the next candidate is still tried. Candidates not yet decided enter P at T = 8,192 exposures; a granted one enters at the extended T. B is read from the config."""
    c = cfg or core.load_config()
    b = float(c["budget"]["b_hours"])
    workers = int(c["budget"]["workers"])
    base_t, ext_t = int(c["ladder"]["base_ceiling_t"]), int(c["ladder"]["extended_ceiling_t"])
    ladder_top = max(c["ladder"]["base"])
    x8_t = ext_t if c["budget"]["x8_in_projection"] else 0
    ordered = core.order_of_candidates(candidates)
    granted: list[str] = []
    out: list[ExtensionDecision] = []
    for ct in ordered:
        assumed = {n: t for n, t in t_known.items()}
        for other in ordered:
            assumed[other.name] = ext_t if other.name in granted else base_t
        assumed[ct.name] = ext_t
        p, _ = projected_hours(
            cts=cts, t_assumed=assumed, granted_rounds=[*granted, ct.name], rates=rates, charged_hours=charged_hours, other_hours=other_hours, x8=x8 if c["budget"]["x8_in_projection"] else None,
            workers=workers, ladder_top=ladder_top, x8_t=x8_t,
        )  # fmt: skip
        ok = p <= b
        if ok:
            granted.append(ct.name)
        out.append(ExtensionDecision(ct.name, ok, p, b))
    return out


def stage_r_cap_hours(cts: Sequence[CellType], rates: Rates, granted_rounds: Sequence[str], cfg: Mapping[str, Any] | None = None) -> float:
    """Stage R's own cap: twice the base-ladder worst case (all runs to the top of the base ladder at stage 3's rates, six workers, one evaluation per ladder point) plus twice the projection of the extension rounds granted."""
    c = cfg or core.load_config()
    workers, factor = int(c["budget"]["workers"]), float(c["budget"]["stage_cap_factor"])
    top = max(c["ladder"]["base"])
    n_points = len(c["ladder"]["base"])
    tasks = [rates.train(arm, ct.slots, ct.updates(top)) + rates.evaluate(arm, ct.slots, n_points) for ct in cts for arm in ("A5-D", "A6") for _ in (1, 2)]
    by_name = {ct.name: ct for ct in cts}
    rounds = sum(extension_round_stage(by_name[n], rates, top).total_seconds for n in granted_rounds)
    return factor * (sum(tasks) / workers) / 3600.0 + factor * (rounds / workers) / 3600.0


# --- reference flags (section 5.2) ---------------------------------------------------------------------------------------------------------------
def reference_flags(a6_at_t: Mapping[int, labels.Obs | None], floor: float, th: Thresholds) -> tuple[labels.RefFlags, dict[str, Any]]:
    """A6 at the cell type's final T on each calibration draw, through conditions 2, 3, 4, 5 and 6 (condition 1 is A6 against itself and is not read). Computed only on a draw where A6's m_P(T) is at or above the floor (ruling 3);
    otherwise REFERENCE BELOW FLOOR AT T is recorded for that draw and no flag is computed on it. A failure on either draw flags that condition. A missing observation (a non-finite A6 run) computes none."""
    flagged: set[int] = set()
    below: list[int] = []
    computed: list[int] = []
    floor_f = Fraction(str(floor))
    for d, obs in sorted(a6_at_t.items()):
        if obs is None:
            continue
        if obs.m_p < floor_f:
            below.append(d)
            continue
        computed.append(d)
        flagged |= set(labels.conditions_failed(obs, obs, th, include_condition_1=False))
    flags = labels.RefFlags(cond4=4 in flagged, other=tuple(sorted(flagged & set(labels.FLAGGABLE_REMOVING))))
    return flags, {"computed_on_draws": computed, "reference_below_floor_at_t_draws": below, "flagged_conditions": sorted(flagged)}


# --- durations.json, events, and the memory rule -----------------------------------------------------------------------------------------------------
def durations_record(entries: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """The ``durations.json`` record: per cell type exactly the whitelisted keys of section 5.2 (iii). Nothing else of Stage R leaves the sealed directory in clear."""
    allowed = {"e_star", "t_exposures", "convergence", "flat_below_floor", "extension", "reference_flags", "reference_below_floor_at_t", "reference_nonfinite", "nonfinite_in_rehearsal", "removed", "labels"}
    for name, e in entries.items():
        extra = set(e) - allowed
        if extra:
            raise ValueError(f"durations.json entry {name!r} has keys outside the whitelist: {sorted(extra)}")
    return {**core.envelope("durations"), "cell_types": {k: dict(v) for k, v in entries.items()}}


def events(entries: Mapping[str, Mapping[str, Any]], cts: Sequence[CellType]) -> list[str]:
    """Section 5.2's events before the freeze, by rule: (a) an anchor cell type carries any reference flag, is NOT SHOWN or prints A5-D FLAT BELOW FLOOR; (b) any reference flag on a load-1 or load-2 cell type; (c) a REFERENCE BELOW
    FLOOR AT T or NON-FINITE IN REHEARSAL entry anywhere. A flag at load 4 or at X8 alone is not an event. In each the study proceeds: this function never returns a stop."""
    out: list[str] = []
    for ct in cts:
        e = entries.get(ct.name)
        if e is None:
            continue
        flags = e.get("reference_flags") or {}
        flagged = bool(flags.get("cond4") or flags.get("other"))
        not_shown = e.get("convergence") in (labels.NOT_SHOWN_REFUSED, labels.NOT_SHOWN_REHEARSAL, "NOT SHOWN")
        if ct.anchor and (flagged or not_shown or e.get("flat_below_floor")):
            out.append(f"(a) anchor {ct.name}: " + ", ".join(x for x, on in (("reference flag", flagged), ("NOT SHOWN", not_shown), (labels.FLAT_BELOW_FLOOR, e.get("flat_below_floor"))) if on))
        if ct.load in (1.0, 2.0) and flagged:
            out.append(f"(b) reference flag at load {ct.load:g}: {ct.name}")
        if e.get("reference_below_floor_at_t") or e.get("nonfinite_in_rehearsal") or e.get("reference_nonfinite"):
            out.append(f"(c) {ct.name}: " + ("REFERENCE BELOW FLOOR AT T" if e.get("reference_below_floor_at_t") else labels.NON_FINITE_REHEARSAL))
    return out


def worker_count(measured_peak_bytes: int, cfg: Mapping[str, Any] | None = None) -> int:
    """The memory rule (section 9, coordinator ruling 3): n = min(6, floor(9 GiB / measured peak per worker)); n < 1 is an engineering stop (never a label, never a dropped cell type)."""
    c = cfg or core.load_config()
    if measured_peak_bytes <= 0 or not math.isfinite(measured_peak_bytes):
        raise EngineeringStop("the measured peak per worker must be positive")
    n = min(int(c["budget"]["workers"]), int(c["resources"]["memory_budget_bytes"]) // int(measured_peak_bytes))
    if n < 1:
        raise EngineeringStop(f"measured peak {measured_peak_bytes} B per worker allows no worker within the memory budget: an engineering stop until the human lead rules")
    return n
