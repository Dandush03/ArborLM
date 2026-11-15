# ruff: noqa: E501
"""P9II classes (ADR-0019 sections 8.1 to 8.7): pure functions from measurements to cell success, arm class at a size, the paired reading against
A0, the negative control, annotations, the Stage 1 and Stage 3 gates, the study outcome, the hypothesis readings, the carry-forward order and the
draw-sensitivity estimators. Nothing here reads a file, trains or evaluates a model; ``stages.analyze`` turns records into the inputs below.

Readings fixed here where the ADR is silent on a formula (all reported, none changes a threshold or a rule):

* A6 reference of a draw: its accuracy on each panel; the draw is NOT_EVALUATED at the size when A6 is missing or below 0.90 on either panel. Condition 1
  compares each panel with A6's accuracy on the same panel.
* Condition 4: H1 and H2 are each compared with the cell's own accuracy on Panel A and on Panel B.
* Time to first success and sustained success: the line is 0.90 x the mean of A6's accuracies on Panels A and B at the readout, on the same draw and size.
* Per-draw accuracy of an arm (DENSE COMPARISON): the mean over the arm's cells in the draw and over both panels; A7's the same over its one cell.
* ADDRESS RECALL per cell: the smaller of the top-8 recalls on Panels A and B; the arm's value is the median over cells.
* SUPERVISION-DEPENDENT: a cell carries it if its probe accuracy at the readout is lower by more than 0.10 than its maximum over the 512 updates before the
  removal of L_addr, or its category counted only from the records after the removal is "collapsed and not recovered"; the arm carries it if more than half
  of its evaluated cells do.
* Stage status NOT_EVALUATED: A0's class at the stage is NOT_EVALUATED (every arm shares the draws and A6, so every arm's class is then NOT_EVALUATED).
* ``Stage 1 is NOT_EVALUATED`` (outcome row 2) is the same statement at Stage 1.
* The exact permutation test of seed exchangeability within draws permutes the cells' outcomes over all cells; its statistic is the number of draws whose
  two cells agree (large = clustered by draw), computed exactly by counting arrangements.
"""

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, NamedTuple

from . import core

# --- labels ---------------------------------------------------------------------------------------------------------------
NOT_EVALUATED, RELIABLE, UNRELIABLE, FAILS = "NOT_EVALUATED", "RELIABLE", "UNRELIABLE", "FAILS"
ARM_CLASSES = (NOT_EVALUATED, RELIABLE, UNRELIABLE, FAILS)
SUCCEEDED, FAILED, CELL_NOT_EVALUATED = "SUCCEEDED", "FAILED", "NOT_EVALUATED"
LM_REDUCED = "LM CAPABILITY REDUCED"
UNRELIABLE_LM = "UNRELIABLE (LM CAPABILITY REDUCED)"
IMPROVES, HARMS, NOT_DISTINGUISHED = "IMPROVES ON A0", "HARMS", "NOT DISTINGUISHED FROM A0"
NEGATIVE_CONTROL_FAILED = "NEGATIVE CONTROL FAILED"
BEATS_DENSE, DENSE_AT_CEILING, DENSE_SUFFICES = "BEATS DENSE", "DENSE AT CEILING", "DENSE SUFFICES"
ALSO_AT_MATCHED_UPDATES, MID_SCHEDULE = "ALSO AT MATCHED UPDATES", "MID-SCHEDULE (not a matched-update run)"
SUPERVISION_DEPENDENT, ADDRESSES_REMAPPED = "SUPERVISION-DEPENDENT", "ADDRESSES RE-MAPPED"
ADDRESS_RECALL, ADDRESS_STABLE = "ADDRESS RECALL", "ADDRESS STABLE"
NEVER_SEPARATED, NEVER_NOT_SEPARATED = "never collapsed and separated", "never collapsed, not separated"
COLLAPSED_RECOVERED, COLLAPSED_NOT_RECOVERED = "collapsed and recovered", "collapsed and not recovered"
CATEGORIES = (NEVER_SEPARATED, NEVER_NOT_SEPARATED, COLLAPSED_RECOVERED, COLLAPSED_NOT_RECOVERED)
# stage statuses
COMPLETE, INCOMPLETE = "COMPLETE", "INCOMPLETE"
NOT_RUN_BUDGET, NOT_RUN_NO_ARM, NOT_RUN_SCHEDULED = "NOT RUN — BUDGET", "NOT RUN — NO ARM PASSED", "NOT RUN — SCHEDULED ARM"
STAGE_STATUSES = (COMPLETE, NOT_RUN_BUDGET, NOT_RUN_NO_ARM, NOT_RUN_SCHEDULED, INCOMPLETE, "NOT_EVALUATED")
SCALE_POSITIVE, SCALE_UNINFORMATIVE = "SCALE PROBE POSITIVE", "SCALE PROBE UNINFORMATIVE"
# outcomes
ENGINEERING_FAIL, NOT_INTERPRETED, NOT_INTERPRETED_INCOMPLETE = "ENGINEERING_FAIL", "NOT_INTERPRETED", "NOT_INTERPRETED (INCOMPLETE)"
INCONCLUSIVE, ANSWER_ONLY_RELIABLE = "INCONCLUSIVE", "ANSWER-ONLY RELIABLE"
ADDRESSING_RELIABLE, ADDRESSING_RELIABLE_4096_ONLY = "ADDRESSING-RELIABLE", "ADDRESSING-RELIABLE AT 4,096 ONLY"
ADDRESSING_RELIABLE_4096_STATUS = "ADDRESSING-RELIABLE AT 4,096; 16,384"
ADDRESSING_UNRELIABLE, ADDRESSING_FAILS = "ADDRESSING-UNRELIABLE", "ADDRESSING-FAILS"
OUTCOMES = (ENGINEERING_FAIL, NOT_INTERPRETED, NOT_INTERPRETED_INCOMPLETE, INCONCLUSIVE, ANSWER_ONLY_RELIABLE, ADDRESSING_RELIABLE, ADDRESSING_RELIABLE_4096_ONLY, ADDRESSING_RELIABLE_4096_STATUS, ADDRESSING_UNRELIABLE, ADDRESSING_FAILS)
CHANGE_ARCHITECTURE = "the recommendation is to change the retrieval architecture, not to spend more compute (section 8.6)"

CellKey = tuple[int, int]  # (draw, seed_index)


# --- measurements ---------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Observation:
    """What the rules read from one cell at one readout (numbers as floats; ``nan`` where the arm has none)."""

    acc_a: float
    acc_b: float
    dep_chance_a: bool  # values permuted and memory disabled both inside the G2 interval, Panel A
    dep_chance_b: bool
    h1: float
    h2: float
    leakage: bool
    distinct_top1: int
    largest_share: float
    probe_facts: int
    lm_rise: float
    address_stability: float = math.nan
    recall_top8: float = math.nan  # the smaller of the Panel A and Panel B top-8 recalls of s(f)
    probe_accuracy: float = math.nan


def observation_from_eval(record: Mapping[str, Any]) -> Observation:
    """``Observation`` of one eval record (``stages`` writes them; non-finite values are read through ``core.number``)."""
    pa, pb = record["panels"]["A"], record["panels"]["B"]
    probe = record.get("probe") or {}
    stats = record.get("panel_statistics") or {}
    recalls = [core.number(stats[k]) for k in ("target_top8_recall_A", "target_top8_recall_B") if k in stats]
    lm = record.get("language_modelling") or {}
    return Observation(
        acc_a=core.number(pa["accuracy"]),
        acc_b=core.number(pb["accuracy"]),
        dep_chance_a=bool(pa.get("memory_dependence_chance", False)),
        dep_chance_b=bool(pb.get("memory_dependence_chance", False)),
        h1=core.number(record["secondary"]["H1"]["accuracy"]),
        h2=core.number(record["secondary"]["H2"]["accuracy"]),
        leakage=bool(pa.get("leakage") or pb.get("leakage")),
        distinct_top1=int(core.number(probe.get("distinct_top1", 0))),
        largest_share=core.number(probe.get("largest_top1_share", 1.0)),
        probe_facts=int(core.number(probe.get("probe_facts", 0))),
        lm_rise=core.number(lm.get("relative_rise", math.nan)),
        address_stability=core.number(stats.get("address_stability", math.nan)),
        recall_top8=min(recalls) if recalls else math.nan,
        probe_accuracy=core.number(probe.get("probe_accuracy", math.nan)),
    )


class A6Reference(NamedTuple):
    acc_a: float
    acc_b: float
    lm_rise: float

    @property
    def usable(self) -> bool:
        return self.acc_a >= core.A6_MIN_ACCURACY and self.acc_b >= core.A6_MIN_ACCURACY  # a NaN is not usable


def slot_condition(distinct: int, largest_share: float, probe_facts: int) -> bool:
    """The slot part of success condition 3: distinct top-1 slots >= 0.50 x the probe facts and the largest top-1 share <= 0.02."""
    return probe_facts > 0 and distinct >= core.DISTINCT_FRACTION * probe_facts and largest_share <= core.LARGEST_SHARE_MAX


@dataclass(frozen=True)
class CellVerdict:
    status: str  # SUCCEEDED | FAILED | NOT_EVALUATED
    failed_conditions: tuple[int, ...] = ()
    lm_flagged: bool = False


def lm_flagged(rise: float, a6_rise: float) -> bool:
    """r > r(A6, same draw and size) + 0.05 (section 8.4 (b), R1); a non-finite r is flagged; a non-finite A6 rise flags nothing."""
    if not math.isfinite(rise):
        return True
    return math.isfinite(a6_rise) and rise > a6_rise + core.LM_MARGIN


def cell_verdict(obs: Observation, a6: A6Reference | None) -> CellVerdict:
    """Section 8.3. NOT_EVALUATED when A6 is missing or below 0.90 (the draw is NOT_EVALUATED at the size); otherwise SUCCEEDED when all five
    conditions hold, FAILED with the numbers of the conditions that do not."""
    if a6 is None or not a6.usable:
        return CellVerdict(CELL_NOT_EVALUATED)
    failed: list[int] = []

    def at_least(value: float, bound: float) -> bool:
        return math.isfinite(value) and value >= bound

    if not (at_least(obs.acc_a, core.SUCCESS_FRACTION_OF_A6 * a6.acc_a) and at_least(obs.acc_b, core.SUCCESS_FRACTION_OF_A6 * a6.acc_b)):
        failed.append(1)
    if not (obs.dep_chance_a and obs.dep_chance_b):
        failed.append(2)
    if not slot_condition(obs.distinct_top1, obs.largest_share, obs.probe_facts):
        failed.append(3)
    if not all(at_least(h, core.HELDOUT_FRACTION * a) for h in (obs.h1, obs.h2) for a in (obs.acc_a, obs.acc_b)):
        failed.append(4)
    if obs.leakage:
        failed.append(5)
    return CellVerdict(FAILED if failed else SUCCEEDED, tuple(failed), lm_flagged(obs.lm_rise, a6.lm_rise))


# --- arm class at a size (section 8.4) --------------------------------------------------------------------------------------
@dataclass(frozen=True)
class ArmClass:
    arm: str
    stage: int
    cls: str  # NOT_EVALUATED | RELIABLE | UNRELIABLE | FAILS
    label: str  # as printed: UNRELIABLE (LM CAPABILITY REDUCED) where it applies
    evaluated: int
    successes: int
    failures: int
    lm_flagged_cells: int
    lm_reduced: bool
    expected: int
    missing: int


def arm_class(arm: str, stage: int, verdicts: Mapping[CellKey, CellVerdict], expected: Sequence[CellKey]) -> ArmClass:
    """First match wins: NOT_EVALUATED (fewer than 14 evaluated cells at Stage 1, fewer than 7 at Stage 2); RELIABLE (at most one failed cell among the
    evaluated cells and no LM CAPABILITY REDUCED); UNRELIABLE (at least 4 successes at Stage 1, 2 at Stage 2); FAILS. Stage 3 has no class."""
    if stage not in core.MIN_EVALUATED:
        raise ValueError("arm classes exist at Stages 1 and 2 only")
    evaluated = {k: v for k, v in verdicts.items() if v.status != CELL_NOT_EVALUATED}
    successes = sum(1 for v in evaluated.values() if v.status == SUCCEEDED)
    failures = len(evaluated) - successes
    flagged = sum(1 for v in evaluated.values() if v.lm_flagged)
    reduced = flagged > core.LM_FLAGGED_CELLS
    missing = sum(1 for k in expected if k not in verdicts)
    if len(evaluated) < core.MIN_EVALUATED[stage]:
        cls, label = NOT_EVALUATED, NOT_EVALUATED
    elif failures <= core.MAX_FAILED_RELIABLE and not reduced:
        cls, label = RELIABLE, RELIABLE
    elif successes >= core.MIN_SUCCESSES[stage]:
        cls = UNRELIABLE
        label = UNRELIABLE_LM if reduced and failures <= core.MAX_FAILED_RELIABLE else UNRELIABLE
    else:
        cls, label = FAILS, FAILS
    return ArmClass(arm, stage, cls, label, len(evaluated), successes, failures, flagged, reduced, len(expected), missing)


# --- paired reading against A0 (section 8.4) ---------------------------------------------------------------------------------
def sign_test_p(b: int, c: int) -> float:
    """Exact two-sided sign-test p-value on ``b`` and ``c`` discordant pairs (1.0 with none)."""
    n = b + c
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, i) for i in range(min(b, c) + 1)) / 2**n
    return float(min(1.0, 2 * tail))


@dataclass(frozen=True)
class Paired:
    arm: str
    label: str
    d: int
    x_only: int  # cells where X succeeds and A0 fails
    a0_only: int
    x_successes: int
    a0_successes: int
    pairs: int
    p_value: float


def paired_against_a0(arm: str, x: Mapping[CellKey, CellVerdict], a0: Mapping[CellKey, CellVerdict]) -> Paired:
    """d(X) = (cells where X succeeds and A0 fails) - (cells where A0 succeeds and X fails) over the paired cells (same draw and seed, both evaluated).
    IMPROVES ON A0: d >= 4 and X has more successes than A0 there; HARMS: d <= -4; else NOT DISTINGUISHED FROM A0."""
    keys = [k for k in x if k in a0 and x[k].status != CELL_NOT_EVALUATED and a0[k].status != CELL_NOT_EVALUATED]
    xs = sum(1 for k in keys if x[k].status == SUCCEEDED)
    a0s = sum(1 for k in keys if a0[k].status == SUCCEEDED)
    b = sum(1 for k in keys if x[k].status == SUCCEEDED and a0[k].status != SUCCEEDED)
    c = sum(1 for k in keys if a0[k].status == SUCCEEDED and x[k].status != SUCCEEDED)
    d = b - c
    label = IMPROVES if d >= core.PAIRED_THRESHOLD and xs > a0s else HARMS if d <= -core.PAIRED_THRESHOLD else NOT_DISTINGUISHED
    return Paired(arm, label, d, b, c, xs, a0s, len(keys), sign_test_p(b, c))


def negative_control_failed(a1s_class: ArmClass | None, a1s_paired: Paired | None) -> bool:
    """NEGATIVE CONTROL FAILED at a size if A1-S IMPROVES ON A0 there or A1-S is RELIABLE there. A1-S UNRELIABLE and NOT DISTINGUISHED is not a failure."""
    if a1s_class is None or a1s_paired is None:
        return False
    return a1s_paired.label == IMPROVES or a1s_class.cls == RELIABLE


# --- the gates between stages (sections 8.4, 8.5) ----------------------------------------------------------------------------
class StageGate(NamedTuple):
    run: bool
    advancing: list[str]  # the arms besides A0 (at most two)
    arms: list[str]  # learned arms of the stage, A0 first
    reason: str


def stage1_gate(classes: Mapping[str, ArmClass], negative_control_failed_4096: bool) -> StageGate:
    """Stage 2 runs if at least one arm is eligible (RELIABLE at Stage 1, not A1-S, and not A1 or A2 skipped by NEGATIVE CONTROL FAILED). A0 runs at
    Stage 2 whenever Stage 2 runs. Besides A0 an arm advances only if RELIABLE; if more than two are, the two first in the order A5-C, A5-D, A4, A2, A1.
    A1-S runs with it when A1 or A2 advances. A pure function of Stage 1's classes: the arms of Stage 2 are never chosen by hand."""
    def eligible(arm: str) -> bool:
        c = classes.get(arm)
        skipped = negative_control_failed_4096 and arm in core.SUPERVISED_ARMS
        return c is not None and c.cls == RELIABLE and not skipped

    pool = [a for a in core.ADVANCE_ORDER if eligible(a)]
    anyone = eligible("A0") or bool(pool)
    if not anyone:
        return StageGate(False, [], [], "no arm is eligible to advance: " + NOT_RUN_NO_ARM)
    advancing = pool[: core.MAX_ADVANCING]
    return StageGate(True, advancing, core.stage2_arms(advancing), "run")


def stage3_gate(classes_16k: Mapping[str, ArmClass], negative_control_failed_16k: bool, stage2_status: str) -> tuple[str | None, str, str | None]:
    """The selected arm and what Stage 3 does. Returns ``(selected, action, status)``: ``action`` is ``run`` or ``not run`` and ``status`` is None when it
    runs, else NOT RUN — NO ARM PASSED (no arm RELIABLE at 16,384) or NOT RUN — SCHEDULED ARM (the selected arm is A2 or A4: no later arm is substituted).
    The selected arm is the first RELIABLE arm at 16,384 (4U) in the carry-forward order, A1 and A2 skipped where NEGATIVE CONTROL FAILED."""
    if stage2_status != COMPLETE:
        return None, "not run", NOT_RUN_NO_ARM
    for arm in core.CARRY_FORWARD_ORDER:
        c = classes_16k.get(arm)
        if c is None or c.cls != RELIABLE or (negative_control_failed_16k and arm in core.SUPERVISED_ARMS):
            continue
        if arm in core.SCHEDULED_ARMS:
            return arm, "not run", NOT_RUN_SCHEDULED
        return arm, "run", None
    return None, "not run", NOT_RUN_NO_ARM


def scale_probe(selected_verdicts: Mapping[CellKey, CellVerdict]) -> dict[str, Any]:
    """Section 8.5: SCALE PROBE POSITIVE if both cells succeed, SCALE PROBE UNINFORMATIVE otherwise (the counts are printed)."""
    successes = sum(1 for v in selected_verdicts.values() if v.status == SUCCEEDED)
    return {"label": SCALE_POSITIVE if successes == len(selected_verdicts) == 2 else SCALE_UNINFORMATIVE, "successes": successes, "cells": len(selected_verdicts), "not_evaluated": sum(1 for v in selected_verdicts.values() if v.status == CELL_NOT_EVALUATED)}


# --- the training-time categories (section 8.1) -------------------------------------------------------------------------------
@dataclass(frozen=True)
class ProbePoint:
    update: int
    distinct: int
    largest_share: float
    probe_facts: int
    mean_cosine: float = math.nan
    probe_accuracy: float = math.nan
    recall_top8: float = math.nan


def probe_points(diagnostics: Sequence[Mapping[str, Any]]) -> list[ProbePoint]:
    out = []
    for r in diagnostics:
        out.append(
            ProbePoint(
                int(r["update"]),
                int(core.number(r.get("distinct_top1", 0))),
                core.number(r.get("largest_top1_share", 1.0)),
                int(core.number(r.get("probe_facts", 0))),
                core.number(r.get("mean_cosine_different", math.nan)),
                core.number(r.get("probe_accuracy", math.nan)),
                core.number(r.get("target_top8_recall", math.nan)),
            )
        )
    return sorted(out, key=lambda p: p.update)


def _separated(p: ProbePoint) -> bool:
    return slot_condition(p.distinct, p.largest_share, p.probe_facts)


@dataclass(frozen=True)
class Category:
    name: str
    onset: int | None
    escape: int | None
    cosine_onset: int | None
    cosine_escape: int | None


def category_of(points: Sequence[ProbePoint], *, after: int = 0) -> Category:
    """The four categories, reported for every cell and never merged. ``points`` are the records in update order, the last one the readout (the probe of
    the readout appended if it is not already the last record). Onset: the first record with at most 32 distinct top-1 slots. Escape: the first later
    record from which, to the end, the slot part of condition 3 holds. Separated (no onset): the same condition at the readout. ``after`` keeps only the
    records after that update (A2: the records after the removal of L_addr). The cosine onset (>= 0.9) and escape (from which, to the end, <= 0.5) are
    reported beside them and enter no rule."""
    pts = [p for p in points if p.update > after]
    if not pts:
        return Category(NEVER_NOT_SEPARATED, None, None, None, None)
    onset_i = next((i for i, p in enumerate(pts) if p.distinct <= core.ONSET_DISTINCT_MAX), None)
    cos_i = next((i for i, p in enumerate(pts) if math.isfinite(p.mean_cosine) and p.mean_cosine >= core.COSINE_ONSET), None)
    cos_escape = None
    if cos_i is not None:
        for i in range(cos_i + 1, len(pts)):
            if all(math.isfinite(q.mean_cosine) and q.mean_cosine <= core.COSINE_ESCAPE for q in pts[i:]):
                cos_escape = pts[i].update
                break
    cos_onset = None if cos_i is None else pts[cos_i].update
    if onset_i is None:
        return Category(NEVER_SEPARATED if _separated(pts[-1]) else NEVER_NOT_SEPARATED, None, None, cos_onset, cos_escape)
    onset = pts[onset_i].update
    for i in range(onset_i + 1, len(pts)):
        if all(_separated(q) for q in pts[i:]):
            return Category(COLLAPSED_RECOVERED, onset, pts[i].update, cos_onset, cos_escape)
    return Category(COLLAPSED_NOT_RECOVERED, onset, None, cos_onset, cos_escape)


def with_readout(points: Sequence[ProbePoint], readout: ProbePoint) -> list[ProbePoint]:
    """The records with the readout's probe as the final point (replacing the last record if it is at the same update)."""
    kept = [p for p in points if p.update < readout.update]
    return [*kept, readout]


def first_success_update(points: Sequence[ProbePoint], line: float) -> int | None:
    """Time to first success: the first record with probe accuracy >= the line (0.90 x A6's readout accuracy)."""
    return next((p.update for p in points if math.isfinite(p.probe_accuracy) and p.probe_accuracy >= line), None)


def sustained_success(points: Sequence[ProbePoint], line: float) -> bool | None:
    """After the first success, no later record falls below the line by more than 0.05; None if there is no first success."""
    first = first_success_update(points, line)
    if first is None:
        return None
    return all(not (p.probe_accuracy < line - core.SUSTAINED_DROP) for p in points if p.update > first and math.isfinite(p.probe_accuracy))


def gradient_ratio(updates: Sequence[Mapping[str, Any]]) -> float:
    """The mean over updates 64 to 1,024 of |grad wq| / |grad wo| of the update log (the answer loss for A0)."""
    ratios = []
    for r in updates:
        u = int(r["update"])
        if core.H19A_RATIO_FROM <= u <= core.H19A_RATIO_TO:
            wo = core.number(r["grad_norm"]["wo"])
            if wo > 0:
                ratios.append(core.number(r["grad_norm"]["wq"]) / wo)
    return sum(ratios) / len(ratios) if ratios else math.nan


def path_length(updates: Sequence[Mapping[str, Any]], groups: Sequence[str], after: int) -> float:
    """The summed per-update movement of ``groups`` over the updates after ``after`` (A2's movement after the removal against A0's over the same updates)."""
    return sum(core.number(r["param_change_norm"][g]) for r in updates if int(r["update"]) > after for g in groups)


def cumulative_path(updates: Sequence[Mapping[str, Any]]) -> tuple[tuple[int, float], ...]:
    """Cumulative per-update movement of the query projection and the keys, sampled every 64 updates and at the last update."""
    total, out = 0.0, []
    for r in sorted(updates, key=lambda r: int(r["update"])):
        total += core.number(r["param_change_norm"]["wq"]) + core.number(r["param_change_norm"]["keys"])
        if int(r["update"]) % core.DIAG_EVERY == 0:
            out.append((int(r["update"]), total))
    if updates and (not out or out[-1][0] != int(max(int(r["update"]) for r in updates))):
        out.append((int(max(int(r["update"]) for r in updates)), total))
    return tuple(out)


def path_after(path: Sequence[tuple[int, float]], after: int) -> float | None:
    """The movement accumulated after update ``after`` from a ``cumulative_path`` (None if ``after`` is not a sampled update)."""
    at = dict(path).get(after)
    return None if at is None or not path else path[-1][1] - at


@dataclass(frozen=True)
class TrainingSummary:
    """What the analysis keeps of a cell's logs."""

    category: Category
    onset_within_256: bool
    gradient_ratio: float
    first_success: int | None
    sustained: bool | None
    supervision_acc_drop: bool | None = None
    supervision_collapse: bool | None = None
    remapped: bool | None = None
    movement_after_removal: float | None = None
    stage_updates: int = 0
    path: tuple[tuple[int, float], ...] = ()  # cumulative movement of wq and keys, sampled every 64 updates and at the end
    u_pre: int | None = None


def summarize_training(
    arm: str,
    updates: Sequence[Mapping[str, Any]],
    diagnostics: Sequence[Mapping[str, Any]],
    readout: ProbePoint,
    a6_line: float,
    *,
    u_pre: int | None = None,
    succeeded: bool = False,
    stage_updates: int = 0,
) -> TrainingSummary:
    """Categories, onset, gradient ratio, time to first success, sustained success and, for A2, the SUPERVISION-DEPENDENT clauses and the ADDRESSES RE-MAPPED
    reading, from a cell's update log and diagnostics (the readout's probe as the last point)."""
    points = with_readout(probe_points(diagnostics), readout)
    cat = category_of(points)
    acc_drop = collapse = remapped = movement = None
    if arm == "A2" and u_pre is not None:
        before = [p.probe_accuracy for p in points if u_pre - core.SUPERVISION_WINDOW < p.update <= u_pre and math.isfinite(p.probe_accuracy)]
        acc_drop = bool(before) and math.isfinite(readout.probe_accuracy) and readout.probe_accuracy < max(before) - core.SUPERVISION_DROP
        collapse = category_of(points, after=u_pre).name == COLLAPSED_NOT_RECOVERED
        at_removal = next((p for p in points if p.update == u_pre), None)
        if at_removal is not None and math.isfinite(at_removal.recall_top8) and math.isfinite(readout.recall_top8):
            remapped = bool(succeeded and at_removal.recall_top8 - readout.recall_top8 > core.SUPERVISION_DROP)
        movement = path_length(updates, ("wq", "keys"), u_pre)
    return TrainingSummary(
        cat,
        cat.onset is not None and cat.onset <= core.H19A_ONSET_UPDATES,
        gradient_ratio(updates),
        first_success_update(points, a6_line),
        sustained_success(points, a6_line),
        acc_drop,
        collapse,
        remapped,
        movement,
        stage_updates,
        cumulative_path(updates),
        u_pre,
    )


# --- annotations (section 8.4) ---------------------------------------------------------------------------------------------------
def median(values: Sequence[float]) -> float:
    return core.median([v for v in values if math.isfinite(v)])


def category_counts(summaries: Mapping[CellKey, TrainingSummary]) -> dict[str, int]:
    out = dict.fromkeys(CATEGORIES, 0)
    for s in summaries.values():
        out[s.category.name] += 1
    return out


def supervision_dependent(summaries: Mapping[CellKey, TrainingSummary]) -> dict[str, Any]:
    flagged = [k for k, s in summaries.items() if s.supervision_acc_drop or s.supervision_collapse]
    return {"label": SUPERVISION_DEPENDENT if len(flagged) * 2 > len(summaries) else None, "cells": len(flagged), "of": len(summaries), "collapse_clause_cells": sum(1 for s in summaries.values() if s.supervision_collapse), "accuracy_clause_cells": sum(1 for s in summaries.values() if s.supervision_acc_drop)}


def address_labels(observations: Mapping[CellKey, Observation], arm: str) -> dict[str, Any]:
    """ADDRESS RECALL (A1, A2: the median over cells of the smaller top-8 recall >= 0.90) and ADDRESS STABLE (every learned arm: the median of the address
    stability >= 0.80); printed, in no class."""
    out: dict[str, Any] = {}
    if arm in ("A1", "A2"):
        m = median([o.recall_top8 for o in observations.values()])
        out["recall"] = {"median": m, "label": ADDRESS_RECALL if math.isfinite(m) and m >= core.RECALL_THRESHOLD else None}
    s = median([o.address_stability for o in observations.values()])
    out["stable"] = {"median": s, "label": ADDRESS_STABLE if math.isfinite(s) and s >= core.STABLE_THRESHOLD else None}
    return out


def dense_comparison(arm_acc: Mapping[int, float], dense_acc: Mapping[int, float]) -> dict[str, Any]:
    """For a RELIABLE arm, paired by draw, first match wins: BEATS DENSE if the median over draws of accuracy(arm) / accuracy(A7) >= 1.10; DENSE AT CEILING if
    the median accuracy of A7 is above 0.909; else DENSE SUFFICES. The per-draw differences and the number of draws on which the arm is higher are printed."""
    draws = sorted(d for d in arm_acc if d in dense_acc)
    ratios = {d: (arm_acc[d] / dense_acc[d] if dense_acc[d] > 0 else (math.inf if arm_acc[d] > 0 else 1.0)) for d in draws}
    median_dense = median([dense_acc[d] for d in draws])
    median_ratio = core.median(list(ratios.values()))  # an infinite ratio (A7 at zero) counts as above 1.10
    if draws and math.isfinite(median_ratio) and median_ratio >= core.BEATS_DENSE_RATIO:
        label = BEATS_DENSE
    elif draws and math.isfinite(median_dense) and median_dense > core.DENSE_CEILING:
        label = DENSE_AT_CEILING
    else:
        label = DENSE_SUFFICES
    return {"label": label, "median_ratio": median_ratio, "median_dense_accuracy": median_dense, "differences": {str(d): arm_acc[d] - dense_acc[d] for d in draws}, "draws_arm_higher": sum(1 for d in draws if arm_acc[d] > dense_acc[d]), "draws": len(draws)}


# --- draw-sensitivity estimands (section 8.7) --------------------------------------------------------------------------------------
def _binom_tail_ge(k: int, n: int, p: float) -> float:
    return float(sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k, n + 1)))


def _bisect(f: Any, lo: float, hi: float) -> float:
    for _ in range(200):
        mid = (lo + hi) / 2
        if f(mid):
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def clopper_pearson_lower(k: int, n: int, alpha: float = 0.05) -> float:
    """The exact lower confidence bound on a binomial probability after ``k`` successes in ``n`` (one-sided at ``alpha``): the p at which P(X >= k) = alpha."""
    if k <= 0:
        return 0.0
    return _bisect(lambda p: _binom_tail_ge(k, n, p) >= alpha, 0.0, 1.0)


def clopper_pearson_upper(k: int, n: int, alpha: float = 0.05) -> float:
    if k >= n:
        return 1.0
    return _bisect(lambda p: _binom_tail_ge(k + 1, n, p) >= 1 - alpha, 0.0, 1.0)


def clopper_pearson(k: int, n: int, level: float = 0.95) -> tuple[float, float]:
    """Two-sided exact interval of a binomial probability."""
    a = (1 - level) / 2
    return clopper_pearson_lower(k, n, a), clopper_pearson_upper(k, n, a)


def permutation_test_clustering(per_draw_successes: Sequence[int]) -> dict[str, Any]:
    """Exact permutation test of seed exchangeability within draws. Each draw has two cells; ``per_draw_successes`` holds 0, 1 or 2 per evaluated draw.
    The cells' outcomes are permuted over all cells; the statistic is the number of draws whose two cells agree. Returns the observed value, the exact
    one-sided p-value P(statistic >= observed) and the null mean. Arrangements are counted exactly (multinomial over draws with 2, 1 and 0 successes)."""
    d = len(per_draw_successes)
    s = sum(per_draw_successes)
    if d == 0:
        return {"draws": 0, "statistic": None, "p_value": math.nan, "null_mean": math.nan}
    observed = sum(1 for v in per_draw_successes if v != 1)
    total = math.comb(2 * d, s)
    mass: dict[int, int] = {}
    for a in range(0, d + 1):
        b = s - 2 * a
        c = d - a - b
        if b < 0 or c < 0:
            continue
        ways = math.factorial(d) // (math.factorial(a) * math.factorial(b) * math.factorial(c)) * 2**b
        mass[a + c] = mass.get(a + c, 0) + ways
    p = sum(w for stat, w in mass.items() if stat >= observed) / total
    mean = sum(stat * w for stat, w in mass.items()) / total
    return {"draws": d, "statistic": observed, "p_value": p, "null_mean": mean}


def anova_log_escape(per_draw: Mapping[int, Sequence[float | None]]) -> dict[str, Any]:
    """Between-draw and within-draw mean squares of log escape update (one-way ANOVA, two seeds per draw, uncensored cells only: a draw enters when both of its
    cells escaped at a recorded update), with the censored count (cells that never escaped or never collapsed are censored)."""
    usable: list[tuple[float, float]] = []
    censored = 0
    for cells in per_draw.values():
        values = [math.log(v) for v in cells if v is not None and v > 0]
        censored += sum(1 for v in cells if v is None or v <= 0)
        if len(values) == 2:
            usable.append((values[0], values[1]))
    d = len(usable)
    if d < 2:
        return {"draws_used": d, "censored_cells": censored, "ms_between": math.nan, "ms_within": math.nan}
    means = [(a + b) / 2 for a, b in usable]
    grand = sum(means) / d
    ms_between = 2 * sum((m - grand) ** 2 for m in means) / (d - 1)
    ms_within = sum((a - m) ** 2 + (b - m) ** 2 for (a, b), m in zip(usable, means, strict=True)) / d
    return {"draws_used": d, "censored_cells": censored, "ms_between": ms_between, "ms_within": ms_within}


def draw_sensitivity(arm: str, verdicts: Mapping[CellKey, CellVerdict], summaries: Mapping[CellKey, TrainingSummary], readout_update: int) -> dict[str, Any]:
    """Section 8.7 per arm and size: the draws x seeds table, the 2/2, 1/2 and 0/2 counts, the within-draw discordance rate, the permutation test, the
    failure rate with its per-draw interval and one-sided per-draw bound, escape updates (censored at the readout), their median and the ANOVA mean squares,
    time to first success and the frequency of sustained success."""
    draws = sorted({d for d, _ in verdicts})
    table: dict[str, dict[str, str]] = {str(d): {str(j): verdicts[(d, j)].status for j in (0, 1) if (d, j) in verdicts} for d in draws}
    evaluated = [d for d in draws if all(verdicts[(d, j)].status != CELL_NOT_EVALUATED for j in (0, 1) if (d, j) in verdicts) and any((d, j) in verdicts for j in (0, 1))]
    per_draw = [sum(1 for j in (0, 1) if verdicts.get((d, j)) is not None and verdicts[(d, j)].status == SUCCEEDED) for d in evaluated]
    counts = {"2/2": per_draw.count(2), "1/2": per_draw.count(1), "0/2": per_draw.count(0)}
    n = len(evaluated)
    both = counts["2/2"]
    escapes: dict[CellKey, int | None] = {k: summaries[k].category.escape for k in summaries}
    censored_value = {k: (v if v is not None else readout_update) for k, v in escapes.items()}
    firsts = [s.first_success for s in summaries.values()]
    sustained = [s.sustained for s in summaries.values() if s.sustained is not None]
    return {
        "arm": arm,
        "table": table,
        "draw_counts": counts,
        "discordance_rate": counts["1/2"] / n if n else math.nan,
        "permutation_test": permutation_test_clustering(per_draw),
        "failure_rate": (n - both) / n if n else math.nan,
        "failure_rate_interval": clopper_pearson(n - both, n) if n else None,
        "per_draw_success_lower_bound_95_one_sided": clopper_pearson_lower(both, n) if n else None,
        "escape_updates": {f"{d}/{j}": v for (d, j), v in sorted(censored_value.items())},
        "escape_censored_cells": sum(1 for v in escapes.values() if v is None),
        "median_escape_update": median([float(v) for v in censored_value.values()]),
        "anova_log_escape": anova_log_escape({d: [escapes.get((d, j)) for j in (0, 1)] for d in draws}),
        "time_to_first_success": {f"{d}/{j}": v for (d, j), v in sorted(((k, s.first_success) for k, s in summaries.items()))},
        "first_success_cells": sum(1 for f in firsts if f is not None),
        "sustained_success_frequency": (sum(1 for s in sustained if s) / len(sustained)) if sustained else None,
    }


# --- hypothesis readings, outcome and carry-forward (section 8.6) -----------------------------------------------------------------------
@dataclass
class SizeAnalysis:
    """The classes and paired readings of one stage, as ``stages`` assembles them (``classes[arm]``, ``paired[arm]`` for every learned arm but A0)."""

    stage: int
    classes: dict[str, ArmClass] = field(default_factory=dict)
    paired: dict[str, Paired] = field(default_factory=dict)
    negative_control_failed: bool = False
    supervision_dependent: dict[str, bool] = field(default_factory=dict)  # A2

    def reliable(self, arm: str) -> bool:
        c = self.classes.get(arm)
        return c is not None and c.cls == RELIABLE

    def skipped(self, arm: str) -> bool:
        return self.negative_control_failed and arm in core.SUPERVISED_ARMS

    def paired_label(self, arm: str) -> str:
        p = self.paired.get(arm)
        return "is the reference of every pairing" if arm == "A0" else (p.label if p else "no paired reading")


def hypothesis_readings(s1: SizeAnalysis, h19a_inputs: Mapping[str, Any], *, reading_stage: SizeAnalysis | None = None) -> dict[str, dict[str, Any]]:
    """The readings of section 8.6, fixed in advance. ``h19a_inputs`` holds A0's per-cell ``onset_within_256`` and ``gradient_ratio_le`` counts (of 16).
    H19-B, C, D, F, G are read at 4,096 (Stage 1); ``reading_stage`` replaces it (16,384 at 4U) in the case of the ANSWER-ONLY RELIABLE row."""
    s = reading_stage or s1
    a0 = s1.classes.get("A0")
    h19a = bool(a0 is not None and h19a_inputs["onset_cells"] >= core.H19A_CELLS and h19a_inputs["ratio_cells"] >= core.H19A_CELLS and a0.cls != RELIABLE)

    def read(arm: str, extra: bool = True) -> dict[str, Any]:
        paired = s.paired.get(arm)
        supported = s.reliable(arm) and paired is not None and paired.label == IMPROVES and extra
        contradicted = paired is not None and paired.label == HARMS
        return {"arm": arm, "reading": "CONTRADICTED" if contradicted else ("supported" if supported else "not supported"), "paired": paired.label if paired else None}

    out: dict[str, dict[str, Any]] = {
        "H19-A": {"reading": "supported" if h19a else "not supported", "onset_cells": h19a_inputs["onset_cells"], "ratio_cells": h19a_inputs["ratio_cells"]},
        "H19-B": read("A1", not s.negative_control_failed),
        "H19-C": read("A2", not s.negative_control_failed and not s.supervision_dependent.get("A2", False)),
        "H19-D": read("A4"),
        "H19-F": read("A5-C"),
        "H19-G": read("A5-D"),
    }
    for arm in core.LEARNED_ARMS:
        c = s1.classes.get(arm)
        out[f"H19-E ({arm})"] = {"reading": "supported" if c is not None and c.cls == RELIABLE else "not supported"}
    return out


def carry_forward(s2: SizeAnalysis | None) -> str | None:
    """The interface carried forward: the first RELIABLE arm at 16,384 (4U) in the order A0, A5-C, A5-D, A4, A2, A1 (A1 and A2 skipped where NEGATIVE
    CONTROL FAILED); RELIABLE already excludes an arm that carries LM CAPABILITY REDUCED."""
    if s2 is None:
        return None
    return next((a for a in core.CARRY_FORWARD_ORDER if s2.reliable(a) and not s2.skipped(a)), None)


def _label_of(arm: str, s1: SizeAnalysis, s2: SizeAnalysis | None) -> str:
    sup = core.SUPERVISION_LABEL[arm]
    paired = f"paired against A0 at 4,096: {s1.paired_label(arm)}"
    if s2 is not None and arm in s2.classes:
        paired += f"; at 16,384: {s2.paired_label(arm)}"
    return f"{arm} {sup}, {paired}"


class Outcome(NamedTuple):
    outcome: str
    label: str
    row: int
    arm: str | None
    detail: dict[str, Any]


def study_outcome(s1: SizeAnalysis, s2: SizeAnalysis | None, stage2_status: str, *, stage1_status: str = COMPLETE) -> Outcome:
    """The outcome rows 2 to 8 of section 8.6 (row 1, engineering failure, incompleteness and failed gates, is decided before: ``assess``). First match wins.
    Labels carry the arm, its paired label against A0 and its supervision class."""
    a0 = s1.classes.get("A0")
    if stage1_status == "NOT_EVALUATED" or (a0 is not None and a0.cls == NOT_EVALUATED):
        return Outcome(INCONCLUSIVE, "INCONCLUSIVE (Stage 1 is NOT_EVALUATED)", 2, None, {})
    label_free = [a for a in core.LABEL_FREE_ARMS if s1.reliable(a)]
    if s1.negative_control_failed and not label_free:
        return Outcome(INCONCLUSIVE, "INCONCLUSIVE (NEGATIVE CONTROL FAILED at 4,096 and no label-free arm is RELIABLE there)", 2, None, {})
    if s1.reliable("A0"):
        a0_class_16k = s2.classes["A0"].label if s2 is not None and "A0" in s2.classes else "not run"
        return Outcome(
            ANSWER_ONLY_RELIABLE,
            f"ANSWER-ONLY RELIABLE: A0 (LABEL-FREE), the reference of every pairing; Stage 2 status {stage2_status}; A0's Stage 2 class {a0_class_16k}",
            3, "A0", {"stage2_status": stage2_status, "a0_stage2_class": a0_class_16k},
        )  # fmt: skip
    candidates = [a for a in core.CARRY_FORWARD_ORDER[1:] if s1.reliable(a) and not s1.skipped(a)]
    if candidates:
        both = [a for a in candidates if s2 is not None and s2.reliable(a) and not s2.skipped(a)]
        if stage2_status == COMPLETE and both:
            arm = both[0]
            return Outcome(ADDRESSING_RELIABLE, f"ADDRESSING-RELIABLE: {_label_of(arm, s1, s2)}", 4, arm, {})
        arm = candidates[0]
        if stage2_status == COMPLETE:
            return Outcome(ADDRESSING_RELIABLE_4096_ONLY, f"ADDRESSING-RELIABLE AT 4,096 ONLY: {_label_of(arm, s1, s2)}", 5, arm, {})
        return Outcome(ADDRESSING_RELIABLE_4096_STATUS, f"ADDRESSING-RELIABLE AT 4,096; 16,384 {stage2_status}: {_label_of(arm, s1, None)} (not read as a failure to scale)", 6, arm, {"stage2_status": stage2_status})
    others = [a for a in core.LEARNED_ARMS if a != "A1-S" and a in s1.classes and not s1.skipped(a)]
    if any(s1.classes[a].cls == UNRELIABLE for a in others):
        return Outcome(ADDRESSING_UNRELIABLE, "ADDRESSING-UNRELIABLE: no learned arm is RELIABLE at 4,096; " + CHANGE_ARCHITECTURE, 7, None, {})
    return Outcome(ADDRESSING_FAILS, "ADDRESSING-FAILS: every learned arm other than A1-S FAILS at 4,096; " + CHANGE_ARCHITECTURE, 8, None, {})
