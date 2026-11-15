# ruff: noqa: E501
"""P10S0 classes (ADR-0020 sections 8.2 to 8.7): pure functions from measurements to cell success under S0's criteria and under P9-II's criteria, the arm class per cell type
(20-cell, 10-cell and probe rows of section 8.3), the paired reading (both criteria), replication of P9-II, ADDRESS STABLE, the cross-study consistency rule, the preference order and the
candidate, the annotations on the candidate, the study outcome (first match wins) and the hypothesis readings. Nothing here reads a file, trains or evaluates a model.

Readings fixed here where the ADR is silent on a formula (all reported, none changes a threshold or a rule):

* A6 reference of a draw at a cell type: its accuracy on each panel; the draw is NOT_EVALUATED there when A6 is missing or below 0.90 on either panel (0.50 at 8K/4K, section 8.2).
* A cell succeeds under P9-II's criteria when conditions 1-5 of ADR-0019 section 8.3 hold (``studies.p9ii.classes`` formulas), and under S0's criteria when condition 6 holds too:
  a_use >= 0.95 x accuracy on Panel A and on Panel B. A non-finite value fails the condition.
* A draw is failed (section 8.5 (b)) when any of its evaluated cells fails under P9-II's criteria; it is NOT_EVALUATED when A6 is unusable on it.
* ADDRESS STABLE is the median over the arm's evaluated cells of the address stability (Panel A against Panel B top-1 slots) at the readout, at least 0.80.
* WX cells are compared with the A6 and A7 cells of their own draw and cell type (section 6.2).
"""

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from studies.p9ii import classes as p9c
from studies.p9ii.classes import CellKey, CellVerdict, Observation, Paired

from . import core

NOT_EVALUATED, RELIABLE, UNRELIABLE, FAILS = p9c.NOT_EVALUATED, p9c.RELIABLE, p9c.UNRELIABLE, p9c.FAILS
SUCCEEDED, FAILED, CELL_NOT_EVALUATED = p9c.SUCCEEDED, p9c.FAILED, p9c.CELL_NOT_EVALUATED
UNRELIABLE_LM = p9c.UNRELIABLE_LM
IMPROVES, HARMS, NOT_DISTINGUISHED = p9c.IMPROVES, p9c.HARMS, p9c.NOT_DISTINGUISHED
ADDRESS_STABLE = p9c.ADDRESS_STABLE
S0_CRITERIA, P9II_CRITERIA = "S0", "P9II"
CRITERIA = (S0_CRITERIA, P9II_CRITERIA)
REPLICATES, NOT_REPLICATE, NOT_COMPARABLE = "REPLICATES P9-II", "DOES NOT REPLICATE P9-II", "NOT COMPARABLE"
CONSISTENT, INCONSISTENT, SINGLE_STUDY = "CONSISTENT ACROSS STUDIES", "INCONSISTENT ACROSS STUDIES", "SINGLE-STUDY EVIDENCE"
ANSWER_ONLY_SUFFICES = "(ANSWER-ONLY SUFFICES)"
COLLAPSE_FREE = "COLLAPSE-FREE"

# outcomes (section 8.7)
OUT_NOT_STARTED = core.NOT_STARTED
OUT_ENGINEERING = "ENGINEERING_FAIL / INCOMPLETE"
OUT_INCONCLUSIVE = "INCONCLUSIVE"
OUT_QUALIFIED = "ADDRESSING-QUALIFIED (4,096 AND 16,384)"
OUT_QUALIFIED_4096 = "ADDRESSING-QUALIFIED AT 4,096 ONLY"
OUT_NOT_QUALIFIED = "ADDRESSING-NOT-QUALIFIED"
OUTCOMES = (OUT_NOT_STARTED, OUT_ENGINEERING, OUT_INCONCLUSIVE, OUT_QUALIFIED, OUT_QUALIFIED_4096, OUT_NOT_QUALIFIED)
OUTCOME_ROWS = {OUT_NOT_STARTED: 1, OUT_ENGINEERING: 2, OUT_INCONCLUSIVE: 3, OUT_QUALIFIED: 4, OUT_QUALIFIED_4096: 5, OUT_NOT_QUALIFIED: 6}
NOT_QUALIFIED_TEXT = "NOT QUALIFIED IN S0"
NOT_QUALIFIED_NEUTRAL = "No tested arm met S0's criteria on S0's draws. This text makes no statement about S1 or S2 (ADR-0020 section 17 item 0)."

# block statuses (section 8.7)
COMPLETE, INCOMPLETE = "COMPLETE", "INCOMPLETE"
NOT_RUN_NO_CANDIDATE, NOT_RUN_BUDGET, NOT_RUN_MEMORY = "NOT RUN — NO CANDIDATE", "NOT RUN — BUDGET", "NOT RUN — MEMORY"

Obs = Observation


@dataclass(frozen=True)
class SObservation(Observation):
    """``studies.p9ii.classes.Observation`` plus a_use on both panels (the read swap) and the accuracies' share."""

    a_use_a: float = math.nan
    a_use_b: float = math.nan


def observation_from_eval(record: Mapping[str, Any]) -> SObservation:
    base = p9c.observation_from_eval(record)
    swap = record.get("read_swap") or {}
    a = core.number((swap.get("A") or {}).get("a_use", math.nan))
    b = core.number((swap.get("B") or {}).get("a_use", math.nan))
    return SObservation(**{k: getattr(base, k) for k in Observation.__dataclass_fields__}, a_use_a=a, a_use_b=b)


class A6Ref(p9c.A6Reference):
    """A6's panel accuracies and relative LM rise on a draw; ``usable_at`` depends on the cell type (0.90; 0.50 at 8K/4K)."""

    def usable_at(self, celltype: str) -> bool:
        floor = core.A6_MIN_ACCURACY_OVERLOAD if celltype == "8K/4K" else core.A6_MIN_ACCURACY
        return bool(self.acc_a >= floor and self.acc_b >= floor)  # a NaN is not usable


def _at_least(value: float, bound: float) -> bool:
    return math.isfinite(value) and value >= bound


def cell_verdict(obs: SObservation, a6: p9c.A6Reference | None, celltype: str, criteria: str = S0_CRITERIA) -> CellVerdict:
    """Section 8.2. NOT_EVALUATED when A6 is missing or below its floor on the draw; else SUCCEEDED when conditions 1-5 (P9-II's criteria) hold, and for S0's criteria condition 6 too;
    FAILED with the numbers of the conditions that do not."""
    if criteria not in CRITERIA:
        raise ValueError(f"unknown criteria {criteria!r}")
    ref = A6Ref(*a6) if a6 is not None else None
    if ref is None or not ref.usable_at(celltype):
        return CellVerdict(CELL_NOT_EVALUATED)
    failed: list[int] = []
    if not (_at_least(obs.acc_a, core.SUCCESS_FRACTION_OF_A6 * ref.acc_a) and _at_least(obs.acc_b, core.SUCCESS_FRACTION_OF_A6 * ref.acc_b)):
        failed.append(1)
    if not (obs.dep_chance_a and obs.dep_chance_b):
        failed.append(2)
    if not p9c.slot_condition(obs.distinct_top1, obs.largest_share, obs.probe_facts):
        failed.append(3)
    if not all(_at_least(h, 0.90 * a) for h in (obs.h1, obs.h2) for a in (obs.acc_a, obs.acc_b)):
        failed.append(4)
    if obs.leakage:
        failed.append(5)
    if criteria == S0_CRITERIA and not (_at_least(obs.a_use_a, core.DEPENDENCE_FRACTION * obs.acc_a) and _at_least(obs.a_use_b, core.DEPENDENCE_FRACTION * obs.acc_b)):
        failed.append(6)
    return CellVerdict(FAILED if failed else SUCCEEDED, tuple(failed), p9c.lm_flagged(obs.lm_rise, ref.lm_rise))


# --- arm class per cell type (section 8.3) -------------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class SClass:
    """The class of an arm at a cell type. ``rule`` is '20' or '10'; draw counts are in draws (a draw with any failed evaluated cell is failed)."""

    cls: str
    label: str
    rule: str
    evaluated: int
    successes: int
    failures: int
    lm_flagged_cells: int
    lm_reduced: bool
    expected: int
    missing: int
    draws_evaluated: int
    draws_not_evaluated: int
    draws_failed: int
    draws_succeeded: int
    per_draw_bound: float | None


def per_draw_bound(k: int, n: int) -> float:
    """One-sided 95% Clopper-Pearson lower bound on the per-draw success probability (section 6.3)."""
    return p9c.clopper_pearson_lower(k, n, core.PER_DRAW_BOUND_ALPHA)


def draw_outcomes(verdicts: Mapping[CellKey, CellVerdict]) -> dict[int, str]:
    """Per draw: NOT_EVALUATED (a cell is not evaluated: A6 unusable), FAILED (an evaluated cell failed) or SUCCEEDED (every cell succeeded; both seeds in two-seed types)."""
    out: dict[int, str] = {}
    for draw in sorted({d for d, _ in verdicts}):
        cells = [v for (d, _), v in verdicts.items() if d == draw]
        if any(v.status == CELL_NOT_EVALUATED for v in cells):
            out[draw] = CELL_NOT_EVALUATED
        elif all(v.status == SUCCEEDED for v in cells):
            out[draw] = SUCCEEDED
        else:
            out[draw] = FAILED
    return out


def arm_class(verdicts: Mapping[CellKey, CellVerdict], expected: Sequence[CellKey], rule: str) -> SClass:
    """First match wins: NOT_EVALUATED (more than one draw NOT_EVALUATED); RELIABLE (at most one failed cell of the evaluated cells and no LM CAPABILITY REDUCED; 'no draw with both
    seeds failed' is implied); UNRELIABLE (at least 5 successes of 20 cells, 3 of 10); FAILS. UNRELIABLE and FAILS enter no rule."""
    if rule not in core.MIN_SUCCESSES:
        raise ValueError("rule is '20' or '10'")
    outcomes = draw_outcomes(verdicts)
    evaluated = {k: v for k, v in verdicts.items() if v.status != CELL_NOT_EVALUATED}
    successes = sum(1 for v in evaluated.values() if v.status == SUCCEEDED)
    failures = len(evaluated) - successes
    flagged = sum(1 for v in evaluated.values() if v.lm_flagged)
    reduced = flagged > core.LM_FLAGGED_CELLS
    ne_draws = sum(1 for s in outcomes.values() if s == CELL_NOT_EVALUATED)
    failed_draws = sum(1 for s in outcomes.values() if s == FAILED)
    ok_draws = sum(1 for s in outcomes.values() if s == SUCCEEDED)
    both_failed = any(all(verdicts[(d, j)].status == FAILED for (dd, j) in verdicts if dd == d) and sum(1 for (dd, _) in verdicts if dd == d) > 1 for d in outcomes)
    missing = sum(1 for k in expected if k not in verdicts)
    if ne_draws > core.MAX_NOT_EVALUATED_DRAWS:
        cls, label = NOT_EVALUATED, NOT_EVALUATED
    elif failures <= core.MAX_FAILED_RELIABLE and not both_failed and not reduced:
        cls, label = RELIABLE, RELIABLE
    elif successes >= core.MIN_SUCCESSES[rule]:
        cls = UNRELIABLE
        label = UNRELIABLE_LM if reduced and failures <= core.MAX_FAILED_RELIABLE else UNRELIABLE
    else:
        cls, label = FAILS, FAILS
    n_eval_draws = ok_draws + failed_draws
    bound = per_draw_bound(ok_draws, n_eval_draws) if n_eval_draws else None
    return SClass(cls, label, rule, len(evaluated), successes, failures, flagged, reduced, len(expected), missing, n_eval_draws, ne_draws, failed_draws, ok_draws, bound)


def probe_status(verdicts: Mapping[CellKey, CellVerdict], a6_evaluated: Mapping[int, bool]) -> dict[str, Any]:
    """The 65,536 probe (section 8.3 last column, 8.6): no class, counts only. Any draw NOT_EVALUATED makes the block NOT_EVALUATED. ``a6_evaluated`` is per draw."""
    outcomes = draw_outcomes(verdicts)
    ne = [d for d, s in outcomes.items() if s == CELL_NOT_EVALUATED] + [d for d, ok in a6_evaluated.items() if not ok and d not in outcomes]
    successes = sum(1 for s in outcomes.values() if s == SUCCEEDED)
    n = len(outcomes)
    if ne:
        return {"status": "NOT_EVALUATED", "successes": successes, "draws": n, "label": "NOT_EVALUATED", "per_draw_bound": None}
    label = f"{successes} of {n} succeed" + (f" (per-draw bound {per_draw_bound(3, 3):.3f})" if successes == n == 3 else "")
    return {"status": "COMPLETE", "successes": successes, "draws": n, "label": label, "per_draw_bound": per_draw_bound(successes, n) if n else None}


# --- paired comparison (section 8.4) ---------------------------------------------------------------------------------------------------------------------
def paired(arm: str, x: Mapping[CellKey, CellVerdict], a0: Mapping[CellKey, CellVerdict]) -> Paired:
    """d(X) over the paired cells (same draw and seed, both evaluated); IMPROVES ON A0 if d >= 4 and X has more successes; HARMS if d <= -4; else NOT DISTINGUISHED FROM A0.
    ``studies.p9ii.classes.paired_against_a0``."""
    return p9c.paired_against_a0(arm, x, a0)


def h20d_note(a0_failed_cells_at_8k16k: int) -> str | None:
    """Section 2, H20-D: if A0 fails fewer than four of its 20 cells at 8K/16K, IMPROVES ON A0 cannot be reached and H20-D reads 'not supported' whatever A5-D does."""
    if a0_failed_cells_at_8k16k < core.PAIRED_THRESHOLD:
        return f"A0 fails {a0_failed_cells_at_8k16k} of its cells at 8K/16K, fewer than four: IMPROVES ON A0 is unreachable and H20-D reads not supported, whatever A5-D does (the registered reading)"
    return None


# --- replication and address stability (section 8.4) ---------------------------------------------------------------------------------------------------------
def replication(s0_p9ii_criteria_class: str, p9ii: Mapping[str, Any] | None) -> str:
    """REPLICATES P9-II if the arm is RELIABLE in both studies or not RELIABLE in both; DOES NOT REPLICATE if RELIABLE in exactly one; NOT COMPARABLE if either is NOT_EVALUATED or P9-II
    has no class for the arm at that size."""
    if p9ii is None or not p9ii.get("available") or p9ii.get("base_class") == NOT_EVALUATED or s0_p9ii_criteria_class == NOT_EVALUATED:
        return NOT_COMPARABLE
    return REPLICATES if (s0_p9ii_criteria_class == RELIABLE) == (p9ii["base_class"] == RELIABLE) else NOT_REPLICATE


def address_stable(observations: Mapping[CellKey, SObservation], verdicts: Mapping[CellKey, CellVerdict]) -> dict[str, Any]:
    """ADDRESS STABLE: the median over the evaluated cells of the address stability >= 0.80 (printed, in no class; with the class it is the 'meets the criteria' rule of section 8.5)."""
    values = [o.address_stability for k, o in observations.items() if k in verdicts and verdicts[k].status != CELL_NOT_EVALUATED]
    m = p9c.median(values)
    return {"median": m, "label": ADDRESS_STABLE if math.isfinite(m) and m >= core.STABLE_THRESHOLD else None, "cells": len(values)}


def meets_criteria(s0: SClass, stable: Mapping[str, Any]) -> bool:
    """An arm meets the criteria at a core size if it is RELIABLE there under S0's criteria and ADDRESS STABLE there (section 8.5)."""
    return s0.cls == RELIABLE and stable.get("label") == ADDRESS_STABLE


def added_criterion_failed(p9ii_criteria_class: str, s0: SClass, stable: Mapping[str, Any]) -> str | None:
    """Section 8.7 row 6: where an arm is RELIABLE under P9-II's criteria but not under S0's, the added criterion it failed (condition 6); where it is RELIABLE under S0's but not ADDRESS STABLE,
    that one."""
    if p9ii_criteria_class == RELIABLE and s0.cls != RELIABLE:
        return "condition 6 (fact-specific dependence)"
    if s0.cls == RELIABLE and stable.get("label") != ADDRESS_STABLE:
        return "ADDRESS STABLE"
    return None


# --- consistency across studies (section 8.5) ---------------------------------------------------------------------------------------------------------------------
def consistency(p9ii: Mapping[str, Any] | None, s0_draws_evaluated: int, s0_draws_failed_p9ii_criteria: int) -> dict[str, Any]:
    """CONSISTENT ACROSS STUDIES at a size if (a) P9-II's class is not available or is NOT_EVALUATED (then the label says SINGLE-STUDY EVIDENCE), or (b) P9-II did not print LM CAPABILITY REDUCED
    for the arm at that size and at most two draws failed among the evaluated draws of both studies (a draw fails when any evaluated cell fails under P9-II's criteria). Otherwise INCONSISTENT."""
    if p9ii is None or not p9ii.get("available") or p9ii.get("base_class") == NOT_EVALUATED:
        return {"label": SINGLE_STUDY, "consistent": True, "single_study": True, "p9ii_class": None if p9ii is None else p9ii.get("class"), "failed_draws": s0_draws_failed_p9ii_criteria, "evaluated_draws": s0_draws_evaluated, "pooled_failed": None, "pooled_n": None}
    pooled_failed = int(p9ii["failed_draws"]) + s0_draws_failed_p9ii_criteria
    pooled_n = int(p9ii["evaluated_draws"]) + s0_draws_evaluated
    ok = (not p9ii["lm_reduced"]) and pooled_failed <= core.CONSISTENCY_MAX_FAILED_DRAWS
    return {"label": CONSISTENT if ok else INCONSISTENT, "consistent": ok, "single_study": False, "p9ii_class": p9ii["class"], "failed_draws": s0_draws_failed_p9ii_criteria, "evaluated_draws": s0_draws_evaluated, "pooled_failed": pooled_failed, "pooled_n": pooled_n}


def inconsistent_label(c: Mapping[str, Any]) -> str:
    """Section 8.5 item 4 (and 8.7 row 5): RELIABLE IN S0; INCONSISTENT ACROSS STUDIES (P9-II <class>; pooled <failed> of <n> draws failed)."""
    return f"RELIABLE IN S0; INCONSISTENT ACROSS STUDIES (P9-II {c['p9ii_class']}; pooled {c['pooled_failed']} of {c['pooled_n']} draws failed)"


def pooled_line(p9ii: Mapping[str, Any] | None, s0: SClass, s0_draws_failed_p9ii_criteria: int, arm: str) -> dict[str, Any]:
    """The descriptive pooled count of the two studies under P9-II's criteria (cell types whose protocol is P9-II's only); NOT AVAILABLE where P9-II has no class. No pooled per-draw bound is printed
    for A5-D (its P9-II records are those it was chosen on, section 3.4 sentence)."""
    if p9ii is None or not p9ii.get("available"):
        return {"available": False, "text": "NOT AVAILABLE"}
    n = int(p9ii["evaluated_draws"]) + s0.draws_evaluated
    ok = (int(p9ii["evaluated_draws"]) - int(p9ii["failed_draws"])) + (s0.draws_evaluated - s0_draws_failed_p9ii_criteria)
    bound = None if arm == "A5-D" or n == 0 else per_draw_bound(ok, n)
    text = f"{ok} of {n} draws succeeded (P9-II {int(p9ii['evaluated_draws']) - int(p9ii['failed_draws'])} of {int(p9ii['evaluated_draws'])}; S0 {s0.draws_evaluated - s0_draws_failed_p9ii_criteria} of {s0.draws_evaluated})"
    return {"available": True, "successes": ok, "draws": n, "per_draw_bound": bound, "text": text + ("; no pooled per-draw bound is printed for A5-D" if arm == "A5-D" else f"; pooled per-draw bound {bound:.3f}" if bound is not None else "")}


# --- the candidate (section 8.5) ---------------------------------------------------------------------------------------------------------------------------------
def scope_text(sizes: Sequence[str]) -> str:
    return "4,096 AND 16,384" if tuple(sizes) == core.CORE_CELLTYPES else "4,096 ONLY" if tuple(sizes) == ("2K/4K",) else "16,384 ONLY"


def select_candidate(evals: Mapping[str, Mapping[str, Mapping[str, Any]]]) -> dict[str, Any]:
    """The qualified candidate by the fixed preference order A0, C4 (A5-D), A2, A1. ``evals[arm][celltype]`` holds ``meets`` (bool), ``consistency`` (the dict of ``consistency``) for 2K/4K and
    8K/16K. Items 1 to 5 of section 8.5."""
    per_arm: dict[str, dict[str, Any]] = {}
    for arm in core.PREFERENCE_ORDER:
        if arm not in evals:
            continue
        sizes_ok = []
        notes: dict[str, str] = {}
        single: list[str] = []
        for ct in core.CORE_CELLTYPES:
            e = evals[arm].get(ct)
            if e is None:
                continue
            if e["meets"] and e["consistency"]["consistent"]:
                sizes_ok.append(ct)
                if e["consistency"]["single_study"]:
                    single.append(ct)
            elif e["meets"]:
                notes[ct] = inconsistent_label(e["consistency"])
        per_arm[arm] = {"qualifies_at": sizes_ok, "scope": scope_text(sizes_ok) if sizes_ok else None, "inconsistent_notes": notes, "single_study_sizes": single, "both": tuple(sizes_ok) == core.CORE_CELLTYPES, "at_4096": "2K/4K" in sizes_ok}
    candidate = next((a for a, v in per_arm.items() if v["both"]), None)
    qualified_4096 = None if candidate else next((a for a, v in per_arm.items() if v["at_4096"]), None)
    also: list[str] = []
    if candidate is not None or qualified_4096 is not None:
        first = candidate or qualified_4096
        order = list(per_arm)
        for a in order[order.index(first) + 1 :]:  # type: ignore[arg-type]
            v = per_arm[a]
            if v["at_4096"]:
                also.append(f"ALSO QUALIFIES: {a} ({scope_text(v['qualifies_at'])})")
    outcome = OUT_QUALIFIED if candidate else OUT_QUALIFIED_4096 if qualified_4096 else OUT_NOT_QUALIFIED
    return {
        "outcome": outcome, "candidate": candidate, "qualified_4096_only": qualified_4096, "answer_only_suffices": ANSWER_ONLY_SUFFICES if candidate == "A0" else None,
        "also_qualifies": also, "per_arm": per_arm,
    }  # fmt: skip


# --- annotations on the candidate (section 8.6) ---------------------------------------------------------------------------------------------------------------------
OVERLOAD_QUALIFIED, OVERLOAD_NOT_QUALIFIED, OVERLOAD_NOT_EVALUATED = "OVERLOAD-QUALIFIED", "OVERLOAD NOT QUALIFIED", "OVERLOAD NOT_EVALUATED"
OVERLOAD_NOT_RUN = "OVERLOAD NOT RUN — NO TARGET INJECTION"
OVERLOAD_NO_CANDIDATE = "OVERLOAD NOT RUN — NO CANDIDATE"


def overload_label(candidate: str | None, s0: SClass | None) -> str:
    if candidate is None:
        return OVERLOAD_NO_CANDIDATE
    if candidate in core.SUPERVISED:
        return OVERLOAD_NOT_RUN
    if s0 is None:
        return OVERLOAD_NOT_EVALUATED
    return OVERLOAD_QUALIFIED if s0.cls == RELIABLE else OVERLOAD_NOT_EVALUATED if s0.cls == NOT_EVALUATED else OVERLOAD_NOT_QUALIFIED


def record_length_label(wx: Mapping[str, tuple[SClass, Mapping[str, Any]] | None], block_status: str) -> str:
    """RECORD-LENGTH-FREE VARIANT: PASSES (WX RELIABLE and ADDRESS STABLE at 2K/4K and 8K/16K) / PASSES AT 4,096 ONLY / DOES NOT PASS (not evidence that the record length is required) /
    NOT_EVALUATED / NOT RUN. WX is never the qualified interface."""
    if block_status != COMPLETE:
        return "RECORD-LENGTH-FREE VARIANT: NOT_EVALUATED" if block_status == "NOT_EVALUATED" else f"RECORD-LENGTH-FREE VARIANT: {block_status}"
    results = {ct: wx.get(ct) for ct in core.CORE_CELLTYPES}
    if any(v is None for v in results.values()):
        return "RECORD-LENGTH-FREE VARIANT: INCOMPLETE"
    classes = {ct: v for ct, v in results.items() if v is not None}
    if any(v[0].cls == NOT_EVALUATED for v in classes.values()):
        return "RECORD-LENGTH-FREE VARIANT: NOT_EVALUATED"
    ok = {ct: meets_criteria(v[0], v[1]) for ct, v in classes.items()}
    if all(ok.values()):
        return "RECORD-LENGTH-FREE VARIANT: PASSES"
    if ok["2K/4K"]:
        return "RECORD-LENGTH-FREE VARIANT: PASSES AT 4,096 ONLY"
    return "RECORD-LENGTH-FREE VARIANT: DOES NOT PASS (not evidence that the record length is required)"


# --- the study outcome (section 8.7) ---------------------------------------------------------------------------------------------------------------------------------
def q1_inconclusive(a6_evaluated: Mapping[int, bool]) -> bool:
    """Row 3: cell type 2K/4K is NOT_EVALUATED (more than one draw where A6 < 0.90)."""
    return sum(1 for ok in a6_evaluated.values() if not ok) > core.MAX_NOT_EVALUATED_DRAWS


def reason_missing_at_16384(arm: str, ev: Mapping[str, Mapping[str, Any]]) -> str:
    """Row 5: why 16,384 is missing for the arm qualified at 4,096 only: UNRELIABLE, FAILS, NOT_EVALUATED, not ADDRESS STABLE or INCONSISTENT ACROSS STUDIES (P9-II <class>; pooled <failed> of <n>).
    NOT_EVALUATED is not read as a failure."""
    e = ev[arm]["8K/16K"]
    cls = e["s0"].cls
    if cls == NOT_EVALUATED:
        return "NOT_EVALUATED at 16,384 (not read as a failure)"
    if cls != RELIABLE:
        return str(e["s0"].label)
    if e["stable"].get("label") != ADDRESS_STABLE:
        return "not ADDRESS STABLE at 16,384"
    return inconsistent_label(e["consistency"])


@dataclass
class Outcome:
    row: int
    outcome: str
    label: str
    arm: str | None = None
    scope: str | None = None
    detail: dict[str, Any] = field(default_factory=dict)


def study_outcome(
    *,
    not_started: bool,
    engineering: Sequence[str],
    inconclusive: bool,
    selection: Mapping[str, Any],
    evals: Mapping[str, Mapping[str, Mapping[str, Any]]] | None = None,
) -> Outcome:
    """First match wins: 1 NOT STARTED, 2 ENGINEERING_FAIL / INCOMPLETE (a failed gate, a difference between frozen and running anything, a Q1 cell without a record: ``engineering``
    lists the reasons; no scientific label is derived), 3 INCONCLUSIVE, 4 qualified at both sizes, 5 qualified at 4,096 only (with the reason 16,384 is missing), 6 NOT QUALIFIED."""
    if not_started:
        return Outcome(1, OUT_NOT_STARTED, OUT_NOT_STARTED)
    if engineering:
        return Outcome(2, OUT_ENGINEERING, OUT_ENGINEERING, detail={"reasons": list(engineering)})
    if inconclusive:
        return Outcome(3, OUT_INCONCLUSIVE, OUT_INCONCLUSIVE)
    if selection["candidate"] is not None:
        return Outcome(4, OUT_QUALIFIED, OUT_QUALIFIED, arm=selection["candidate"], scope="4,096 AND 16,384")
    if selection["qualified_4096_only"] is not None:
        arm = selection["qualified_4096_only"]
        why = reason_missing_at_16384(arm, evals) if evals is not None else "not read"
        return Outcome(5, OUT_QUALIFIED_4096, f"{OUT_QUALIFIED_4096}; 16,384 missing: {why}", arm=arm, scope="4,096 ONLY", detail={"why_16384_missing": why})
    return Outcome(6, OUT_NOT_QUALIFIED, f"{OUT_NOT_QUALIFIED} ({NOT_QUALIFIED_TEXT})")


# --- hypothesis readings (section 8.7, last paragraph) ---------------------------------------------------------------------------------------------------------------
SUPPORTED, NOT_SUPPORTED, CONTRADICTED, NOT_READ, NOT_TESTED = "supported", "not supported", "CONTRADICTED", "not read", "not tested"


def hypothesis_readings(
    *,
    classes: Mapping[str, Mapping[str, SClass]],
    paired_s0: Mapping[str, Mapping[str, Paired]],
    replication_labels: Mapping[str, Mapping[str, str]],
    outcome: Outcome,
    candidate: str | None,
    overload: str,
    record_length: str,
    probe: Mapping[str, Any] | None,
    probe_a6_evaluated: bool,
    a0_failed_cells_8k16k: int | None,
) -> dict[str, dict[str, Any]]:
    """H20-A..H20-S as fixed in section 8.7. Every reading is a statement about S0's draws, never a success of the science."""
    out: dict[str, dict[str, Any]] = {}
    a0 = classes.get("A0", {})
    if any(a0.get(ct) is None or a0[ct].cls == NOT_EVALUATED for ct in core.CORE_CELLTYPES):
        out["H20-A"] = {"reading": NOT_READ, "why": "A0 NOT_EVALUATED at a core size"}
    else:
        out["H20-A"] = {"reading": SUPPORTED if any(a0[ct].cls != RELIABLE for ct in core.CORE_CELLTYPES) else NOT_SUPPORTED}
    for h, arm in (("H20-B", "A1"), ("H20-C", "A2"), ("H20-D", "A5-D")):
        cl, pr = classes.get(arm, {}), paired_s0.get(arm, {})
        if any(cl.get(ct) is None or pr.get(ct) is None for ct in core.CORE_CELLTYPES):
            out[h] = {"arm": arm, "reading": NOT_READ, "why": "cells missing"}
            continue
        improves = all(cl[ct].cls == RELIABLE and pr[ct].label == IMPROVES for ct in core.CORE_CELLTYPES)
        harms = any(pr[ct].label == HARMS for ct in core.CORE_CELLTYPES)
        out[h] = {"arm": arm, "reading": SUPPORTED if improves else CONTRADICTED if harms else NOT_SUPPORTED, "paired": {ct: pr[ct].label for ct in core.CORE_CELLTYPES}}
        if h == "H20-D" and a0_failed_cells_8k16k is not None and h20d_note(a0_failed_cells_8k16k):
            out[h]["registered_note"] = h20d_note(a0_failed_cells_8k16k)
            out[h]["reading"] = NOT_SUPPORTED if out[h]["reading"] != CONTRADICTED else CONTRADICTED
    for arm, per in replication_labels.items():
        for ct, label in per.items():
            out[f"H20-R ({arm}, {ct})"] = {"reading": SUPPORTED if label == REPLICATES else NOT_SUPPORTED if label == NOT_REPLICATE else NOT_READ, "label": label}
    out["H20-Q"] = {"reading": SUPPORTED if outcome.row == 4 else NOT_SUPPORTED if outcome.row in (5, 6) else NOT_READ}
    out["H20-O"] = {"reading": NOT_TESTED if overload in (OVERLOAD_NOT_RUN, OVERLOAD_NO_CANDIDATE) else SUPPORTED if overload == OVERLOAD_QUALIFIED else NOT_SUPPORTED, "label": overload}
    if candidate is None or outcome.row != 4:
        out["H20-L"] = {"reading": NOT_TESTED, "label": record_length}
        out["H20-S"] = {"reading": NOT_TESTED}
    else:
        out["H20-L"] = {"reading": SUPPORTED if record_length.endswith(": PASSES") else NOT_SUPPORTED if "PASSES" in record_length or "DOES NOT" in record_length else NOT_TESTED, "label": record_length, "note": "a failure of WX is never evidence that the record length is required; H20-L is never contradicted"}
        if probe is None or probe.get("status") != "COMPLETE":
            out["H20-S"] = {"reading": NOT_TESTED if probe is None else NOT_SUPPORTED, "label": None if probe is None else probe.get("label")}
        else:
            k, n = int(probe["successes"]), int(probe["draws"])
            out["H20-S"] = {"reading": SUPPORTED if k == n == 3 else CONTRADICTED if k == 0 and probe_a6_evaluated else NOT_SUPPORTED, "label": probe["label"], "note": "annotation; never part of the label; permits nothing"}
    return out


def readings_mention_a5d(readings: Mapping[str, Mapping[str, Any]]) -> list[str]:
    """Hypothesis lines that name A5-D (the printed block of section 3.4 must accompany them)."""
    return [k for k, v in readings.items() if "A5-D" in k or v.get("arm") == "A5-D"]
