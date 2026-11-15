# ruff: noqa: E501
"""P10S1 verdicts, classes, labels and outcomes (ADR-0021 sections 7 and 8): pure functions of counts and frozen tables, no I/O.

* capacity line: the step verdict of one replicate (8.2), the step class over five replicates (8.3), the arm class (8.4), the control and cost labels (8.5), the descriptive
  labels (8.6) and the capacity outcome (8.7);
* efficiency line: u_T with its censoring, the step verdict (8.8), the step class, the arm class, the dense label and the efficiency outcome;
* the tag ``STORE ONLY; ORACLE-ADDRESSED`` that every positive label carries (section 3 item 4); ``emit`` refuses text with a positive label and no tag.

Readings of the ADR that its text leaves open are marked READING and listed in ``READINGS`` (they are printed in the report and need the lead's review); none changes a
threshold. A condition needing "both panels" holds for a replicate only if it holds on Panel A and on Panel B.

Status: implementation self-checked only. Not independent review, not Astra validation, not human approval.
"""

import math
import re
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, NamedTuple

from . import core

EPS = 1e-12


def ge(a: float, b: float) -> bool:
    return a >= b - EPS


def le(a: float, b: float) -> bool:
    return a <= b + EPS


def lt(a: float, b: float) -> bool:
    return a < b - EPS


def gt(a: float, b: float) -> bool:
    return a > b + EPS


# --- status words ---------------------------------------------------------------------------------------------------------------
NOT_EVALUATED, DEPENDENCE_FAILED = "NOT_EVALUATED", "DEPENDENCE_FAILED"
PANEL_DISAGREE = "PANEL-DISAGREE"
CEILING, CAPACITY, GAIN_ONLY, REVERSED, BEHIND, NULL, FLAT_NOT_LOADED, UNRESOLVED = "CEILING", "CAPACITY", "GAIN WITHIN BUDGET ONLY", "REVERSED", "BEHIND WITHIN BUDGET", "NULL", "FLAT, NOT LOADED", "UNRESOLVED"
CAPACITY_STEP, GAIN_STEP, NOT_REPLICATED, NOT_LOADED, NO_GAIN, MIXED = "CAPACITY STEP", "GAIN WITHIN BUDGET", "NOT REPLICATED", "NOT LOADED", "NO GAIN", "MIXED"
CAPACITY_SUPPORTED, CAPACITY_ONE_TRANSITION, NOT_TESTED_BY_LOAD, CAPACITY_NOT_SUPPORTED, INTERMEDIATE = "CAPACITY_SUPPORTED", "CAPACITY_ONE_TRANSITION", "NOT_TESTED_BY_LOAD", "CAPACITY_NOT_SUPPORTED", "INTERMEDIATE"
NOT_ASSESSED = "NOT_ASSESSED"

CAPACITY_POSITIVE, CAPACITY_NEGATIVE = "CAPACITY-POSITIVE", "CAPACITY-NEGATIVE"
CAPACITY_NOT_TESTED = "CAPACITY NOT TESTED — NO LOADED CELL WITHIN BUDGET"
CAPACITY_INCONCLUSIVE, S1_ENGINEERING_FAILURE, S1_INCOMPLETE = "CAPACITY-INCONCLUSIVE", "S1-ENGINEERING-FAILURE", "S1-INCOMPLETE"
EFFICIENCY_POSITIVE, EFFICIENCY_NEGATIVE, EFFICIENCY_INCONCLUSIVE = "EFFICIENCY-POSITIVE", "EFFICIENCY-NEGATIVE", "EFFICIENCY-INCONCLUSIVE"
DENSE_AHEAD, BEATS_DENSE, DENSE_MATCHES, DENSE_NOT_READ = "DENSE AHEAD", "BEATS DENSE", "DENSE MATCHES", "DENSE NOT READ"
SUBLINEAR, LINEAR_KEY_SCORING = "SUBLINEAR", "LINEAR KEY SCORING"
TREE_AHEAD, TREE_COMPETITIVE, TREE_BEHIND = "TREE_AHEAD", "TREE_COMPETITIVE", "TREE_BEHIND"
SCALES, DOES_NOT_SCALE, NOT_ESTABLISHED = "KNOWLEDGE SCALES WITH MEMORY", "KNOWLEDGE DOES NOT SCALE", "NOT ESTABLISHED"
MC_SHORT, MC_AMBIGUOUS = "MC-SHORT", "MC-AMBIGUOUS"

# --- the tag and the positive labels (section 3 item 4) -------------------------------------------------------------------------------
POSITIVE_LABELS = (
    "CAPACITY STEP", "CAPACITY_SUPPORTED", "CAPACITY-POSITIVE", "EFFICIENCY_SUPPORTED", "EFFICIENCY-POSITIVE", "BEATS DENSE", "KNOWLEDGE SCALES WITH MEMORY", "TREE_AHEAD",
    "Storage half supported, as a necessary condition", "Capacity shown; sublinear active work not shown", "CAPACITY_ONE_TRANSITION", "EFFICIENCY_ONE_TRANSITION", "FASTER STEP",
)  # fmt: skip
_TAG_AFTER = re.compile(r"\s*\[[^\]]*" + re.escape(core.STORE_ONLY_TAG))
_POSITIVE_RE = re.compile(r"(?<![\w-])(" + "|".join(re.escape(p) for p in sorted(POSITIVE_LABELS, key=len, reverse=True)) + r")(?![\w-])")


class UntaggedPositiveLabel(ValueError):
    """A positive label was about to be printed without ``STORE ONLY; ORACLE-ADDRESSED`` (ADR-0021 section 3 item 4)."""


def tagged(label: str, *details: str) -> str:
    """``label [STORE ONLY; ORACLE-ADDRESSED; detail; ...]``."""
    return f"{label} [{'; '.join([core.STORE_ONLY_TAG, *[d for d in details if d]])}]"


def is_positive(label: str) -> bool:
    return bool(_POSITIVE_RE.search(label))


_TAGGED_SPAN = re.compile(r"\[" + re.escape(core.STORE_ONLY_TAG) + r"[^\]]*\]")


def untagged_positive_labels(text: str) -> list[str]:
    """Every positive label in ``text`` that is neither immediately followed by a bracket holding the tag nor inside such a bracket (the tag heads the bracket and covers what it
    lists)."""
    spans = [(m.start(), m.end()) for m in _TAGGED_SPAN.finditer(text)]
    return [m.group(1) for m in _POSITIVE_RE.finditer(text) if not _TAG_AFTER.match(text, m.end()) and not any(a <= m.start() < b for a, b in spans)]


def tag_positives(text: str) -> str:
    """Free text from the analysis (reasons, the decision map) with ``[STORE ONLY; ORACLE-ADDRESSED]`` appended after every positive label that has none."""
    out: list[str] = []
    last = 0
    spans = [(m.start(), m.end()) for m in _TAGGED_SPAN.finditer(text)]
    for m in _POSITIVE_RE.finditer(text):
        if _TAG_AFTER.match(text, m.end()) or any(a <= m.start() < b for a, b in spans):
            continue
        out.append(text[last : m.end()] + f" [{core.STORE_ONLY_TAG}]")
        last = m.end()
    return "".join(out) + text[last:]


def emit(text: str) -> str:
    """The one way text reaches a report: raises ``UntaggedPositiveLabel`` if a positive label has no tag."""
    bad = untagged_positive_labels(text)
    if bad:
        raise UntaggedPositiveLabel(f"positive label(s) without {core.STORE_ONLY_TAG}: {sorted(set(bad))}")
    return text


def printable(label: str, *details: str) -> str:
    """A label ready to print: tagged if it is positive, as it is otherwise."""
    return emit(tagged(label, *details)) if is_positive(label) else label


READINGS = {
    "panels": "READING: a condition that the ADR states 'in a replicate' holds for the replicate only if it holds on Panel A and on Panel B; PANEL-DISAGREE is the verdict when the panels give different verdicts",
    "dep_reads": "READING: the snapshots a capacity verdict reads for DEP are U_P of both cells, the smaller cell's U_MC readout and the snapshots at which i*(N; U_run) and i*(N; U_run/2) and the larger cell's i* are attained",
    "mc_direction": "READING: the costlier cell of a pair is read at U_P and the cheaper at the smallest snapshot of the MC grid whose cumulative cost is at least that; the two cost measures giving different costlier cells is MC-AMBIGUOUS (not established)",
    "movement": "READING: the row-movement ratio printed with a verdict is the larger cell's total value-row movement over the smaller's at U_P, with the without-gradient share ratio beside it; OPTIMIZER-ASSISTED tests the share ratio; efficiency verdicts also print both at each cell's hit snapshot",
    "dense_ahead_panels": "READING: a replicate counts toward DENSE AHEAD (d at most -0.25) only if it holds on both panels",
    "dense_not_read_efficiency": "READING: a FASTER STEP whose larger cell has no D-OQ cell is printed DENSE NOT READ on the efficiency line and is not blocked (the ADR defines the block only for DENSE FASTER)",
    "analytic_madds": "READING: analytic multiply-adds per update = 3 x 128 x W (forward and backward) + 4 x trainable parameters (AdamW), W as section 7.4",
    "knn_information": "READING: i of KNN-W, KNN-W-IVF and DICT is computed from raw accuracy (there is no memory to swap)",
    "robustness": "READING: robustness is read on Panel A only, accuracy retained = mean raw accuracy over three seeded masks",
    "seed_block_readouts": "READING: the seed block's spread is reported at the MU readout (U_P) and at U_run",
    "dense_rate_tie": "PENDING LEAD REVIEW: section 10.1 item 3 says a difference below 0.02 'goes to the faster of the two'; the rule is not defined, so a tie within 0.02 is not resolved by code",
    "mc_snapshot_grid": "READING: a multiplier above 6 has no snapshot on the MC grid and is MC-SHORT",
    "simulation_setting": "PENDING LEAD REVIEW: section 7.5 asks for page misses 'at one setting'; the setting (8 rows per page, rho = 1/4, tie rule asc) is the implementer's pick and is printed",
    "analysis_costs": "PENDING LEAD REVIEW: the ADR does not define 'analytic multiply-adds'; see analytic_madds",
}


# --- observations ---------------------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class PanelObs:
    """Counts of one cell, snapshot and panel (trained answer sites ``n``): ``useful`` is a_use's numerator; ``disabled``, ``shuffled`` and ``swap`` are correct counts under the
    ablations (None where an ablation does not apply)."""

    n: int
    correct: int
    useful: int
    disabled: int | None = None
    shuffled: int | None = None
    swap: int | None = None
    unseen_n: int = 0
    unseen_correct: int = 0

    @property
    def i(self) -> float:
        return core.bits_per_fact(self.useful, self.n)

    @property
    def a_use(self) -> float:
        return self.useful / self.n if self.n else math.nan

    @property
    def accuracy(self) -> float:
        return self.correct / self.n if self.n else math.nan

    @property
    def leakage(self) -> bool:
        return self.unseen_n > 0 and not core.at_chance(self.unseen_correct, self.unseen_n)

    def dep(self, memory: bool = True) -> bool | None:
        """DEP (section 8.1), for a memory cell with a_use >= 0.25: memory disabled gives chance, value shuffle gives chance, a_use >= 0.95 x raw accuracy. None where it does not
        apply (a_use below 0.25, or not a memory cell)."""
        if not memory or self.n <= 0 or lt(self.a_use, core.DEP_USE_FLOOR):
            return None
        ok = self.disabled is not None and core.at_chance(self.disabled, self.n)
        ok = ok and (self.shuffled is None or core.at_chance(self.shuffled, self.n))
        return bool(ok and ge(self.a_use, core.DEP_USE_OF_RAW * self.accuracy))


class View:
    """One panel of one cell's series: i, a_use and DEP by snapshot, i*, plateau and loaded (section 8.2)."""

    def __init__(self, obs: Mapping[int, PanelObs], run: int, u_p: int, *, memory: bool = True) -> None:
        if not obs:
            raise ValueError("a view needs at least one snapshot")
        self.obs, self.run, self.u_p, self.memory = dict(obs), run, u_p, memory
        self.updates = tuple(sorted(self.obs))

    def has(self, u: int) -> bool:
        return u in self.obs

    def i(self, u: int) -> float:
        return self.obs[u].i

    def a_use(self, u: int) -> float:
        return self.obs[u].a_use

    def dep(self, u: int) -> bool | None:
        return self.obs[u].dep(self.memory)

    def i_star(self, limit: int) -> tuple[float, int]:
        """The maximum of i over the snapshots at or below ``limit`` and the first update that attains it."""
        eligible = [u for u in self.updates if u <= limit]
        if not eligible:
            raise ValueError(f"no snapshot at or below {limit}")
        best = max(eligible, key=lambda u: (self.obs[u].i, -u))
        return self.obs[best].i, best

    def plateaued(self) -> bool:
        """i*(c; U_run) - i*(c; U_run/2) at most 0.10 bits per fact."""
        return le(self.i_star(self.run)[0] - self.i_star(self.run // 2)[0], core.PLATEAU_MAX)

    def loaded(self) -> bool:
        """Plateaued and i*(c; U_run) at most 4.0 bits per fact (section 8.2)."""
        return self.plateaued() and le(self.i_star(self.run)[0], core.LOADED_I_MAX)


# --- matched compute (section 5.4) --------------------------------------------------------------------------------------------------------
class McEntry(NamedTuple):
    """The MC readout of a pair of cells: the update of each cell's readout, or the status (MC-SHORT when the matching snapshot exceeds the cheaper cell's run length or the
    multiplier is above the grid; MC-AMBIGUOUS when the two cost measures disagree on the costlier cell)."""

    status: str  # "OK", MC_SHORT or MC_AMBIGUOUS
    small_update: int | None
    large_update: int | None
    multiplier: float
    cheaper: str | None  # "small" or "large"

    def ok(self) -> bool:
        return self.status == "OK"


def match_snapshot(ratios: Sequence[float], u_p: int, cheaper_run: int) -> tuple[str, int | None, float]:
    """The smallest snapshot m x U_P of the MC grid with m at least the larger of the multipliers (``ratios``: costlier cost per update over cheaper cost per update, one per cost
    measure); MC-SHORT when no grid value reaches it or the snapshot is beyond the cheaper cell's run length."""
    mult = max(ratios)
    if not math.isfinite(mult) or mult < 1.0 - EPS:
        return MC_AMBIGUOUS, None, mult
    for g in core.MC_GRID:
        if ge(g, mult):
            update = core.multiple_of(u_p, g)
            return ("OK", update, mult) if update <= cheaper_run else (MC_SHORT, None, mult)
    return MC_SHORT, None, mult


def mc_pair(costs_small: Mapping[str, float], costs_large: Mapping[str, float], u_p: int, run_small: int, run_large: int) -> McEntry:
    """The MC readouts of a (smaller, larger) pair from the two frozen cost measures per update (``cpu`` seconds and ``madds``). The costlier cell is read at U_P, the cheaper at the
    smallest grid snapshot whose cumulative cost is at least the costlier cell's; the larger of the two multipliers is used."""
    ratios = {m: costs_large[m] / costs_small[m] for m in ("cpu", "madds")}
    large_costlier = [r >= 1.0 - EPS for r in ratios.values()]
    if all(large_costlier):
        status, update, mult = match_snapshot(list(ratios.values()), u_p, run_small)
        return McEntry(status, update, u_p if status == "OK" else None, mult, "small")
    if not any(large_costlier) or all(abs(r - 1.0) <= EPS for r in ratios.values()):
        status, update, mult = match_snapshot([1.0 / r for r in ratios.values()], u_p, run_large)
        return McEntry(status, u_p if status == "OK" else None, update, mult, "large")
    return McEntry(MC_AMBIGUOUS, None, None, max(max(ratios.values()), 1.0 / min(ratios.values())), None)


# --- capacity line: step verdict of one replicate (section 8.2) ------------------------------------------------------------------------------
class StepResult(NamedTuple):
    verdict: str
    detail: dict[str, Any]


def _reads(small: View, large: View, mc: McEntry) -> tuple[set[int], set[int]]:
    u_p = small.u_p
    s_run, s_half = small.i_star(small.run)[1], small.i_star(small.run // 2)[1]
    l_run, l_half = large.i_star(large.run)[1], large.i_star(large.run // 2)[1]
    rs, rl = {u_p, s_run, s_half}, {u_p, l_run, l_half}
    if mc.ok():
        rs.add(int(mc.small_update))  # type: ignore[arg-type]
        rl.add(int(mc.large_update))  # type: ignore[arg-type]
    return rs, rl


def capacity_panel(small: View, large: View, mc: McEntry, *, ref_ok: bool, leakage: bool = False) -> StepResult:
    """One panel's verdict for the step N -> 4N (rows 1 to 10 of section 8.2, first match wins). ``ref_ok`` is REF for the row and replicate; ``leakage`` is LEAKAGE in either cell
    (either panel). Delta_MC is read at the MC readouts (the costlier cell at U_P, the cheaper at its matched snapshot); MC-SHORT or MC-AMBIGUOUS leave it undefined, so
    row 4 cannot hold."""
    u_p = small.u_p
    d: dict[str, Any] = {"mc_status": mc.status, "mc_multiplier": mc.multiplier}
    if not ref_ok or leakage:
        return StepResult(NOT_EVALUATED, {**d, "reason": "REF failed" if not ref_ok else "LEAKAGE"})
    i_s_up, i_l_up = small.i(u_p), large.i(u_p)
    i_s_run, _ = small.i_star(small.run)
    i_s_half, _ = small.i_star(small.run // 2)
    i_l_run, _ = large.i_star(large.run)
    d_mu, d_sat, d_full = i_l_up - i_s_up, i_l_up - i_s_run, i_l_run - i_s_run
    d_mc = None
    if mc.ok():
        d_mc = large.i(int(mc.large_update)) - small.i(int(mc.small_update))  # type: ignore[arg-type]
    d.update(i_small_up=i_s_up, i_large_up=i_l_up, delta_mu=d_mu, delta_mc=d_mc, delta_sat=d_sat, delta_full=d_full, i_star_small_run=i_s_run, i_star_small_half=i_s_half, i_star_large_run=i_l_run)
    reads_small, reads_large = _reads(small, large, mc)
    d["dep_failed_small"] = sorted(u for u in reads_small if small.dep(u) is False)
    d["dep_failed_large"] = sorted(u for u in reads_large if large.dep(u) is False)
    if d["dep_failed_small"] or d["dep_failed_large"]:
        return StepResult(DEPENDENCE_FAILED, d)
    loaded, p_small, p_large = small.loaded(), small.plateaued(), large.plateaued()
    d.update(smaller_loaded=loaded, smaller_plateaued=p_small, larger_plateaued=p_large, a_use_large_up=large.a_use(u_p))
    if ge(i_s_up, core.CEILING_I):
        return StepResult(CEILING, d)
    row4 = (
        ge(d_mu, core.GAIN_MIN) and d_mc is not None and ge(d_mc, core.GAIN_MIN) and ge(d_sat, core.GAIN_MIN) and loaded
        and ge(d_sat - 2.0 * (i_s_run - i_s_half), core.GAIN_MIN) and ge(large.a_use(u_p), core.A_USE_FLOOR_CAPACITY)
    )  # fmt: skip
    if row4:
        return StepResult(CAPACITY, d)
    if ge(d_mu, core.GAIN_MIN):
        return StepResult(GAIN_ONLY, d)
    if le(d_mu, -core.GAIN_MIN) and le(d_full, -core.GAIN_MIN):
        return StepResult(REVERSED, d)
    if le(d_mu, -core.GAIN_MIN):
        return StepResult(BEHIND, d)
    if lt(abs(d_mu), core.NULL_MAX) and lt(abs(d_full), core.NULL_MAX) and p_small and p_large:
        return StepResult(NULL if loaded else FLAT_NOT_LOADED, d)
    return StepResult(UNRESOLVED, d)


def capacity_replicate(panels: Mapping[str, StepResult]) -> StepResult:
    """Both panels agree -> that verdict; otherwise PANEL-DISAGREE (section 8.2)."""
    verdicts = {p: r.verdict for p, r in panels.items()}
    detail = {"panels": {p: {"verdict": r.verdict, **r.detail} for p, r in panels.items()}}
    if len(set(verdicts.values())) == 1:
        return StepResult(next(iter(verdicts.values())), detail)
    return StepResult(PANEL_DISAGREE, detail)


def capacity_step_class(verdicts: Sequence[str]) -> str:
    """Step class over the five replicates (section 8.3, first match wins; the denominator is always 5)."""
    if len(verdicts) != core.REPLICATES:
        raise ValueError("a step class needs one verdict per replicate")
    c = Counter(verdicts)
    n = len(verdicts)
    if c[NOT_EVALUATED] >= 2:
        return NOT_EVALUATED
    if c[DEPENDENCE_FAILED] >= 2:
        return DEPENDENCE_FAILED
    if c[PANEL_DISAGREE] >= 2:
        return NOT_REPLICATED
    if c[CAPACITY] == n:
        return CAPACITY_STEP
    if c[CAPACITY] + c[GAIN_ONLY] == n:
        return GAIN_STEP
    if c[CEILING] + c[FLAT_NOT_LOADED] >= core.PAIRED_MOST:
        return NOT_LOADED
    if c[REVERSED] >= core.PAIRED_MOST:
        return REVERSED
    if c[NULL] + c[REVERSED] >= core.PAIRED_MOST:
        return NO_GAIN
    return MIXED


def capacity_arm_class(step_classes: Mapping[str, str], transitions: Mapping[str, Sequence[str]], a_use_largest_all5: bool) -> str:
    """Arm class (section 8.4, first match wins). ``step_classes`` maps a step name to its step class, ``transitions`` a transition name to its step names,
    ``a_use_largest_all5`` is a_use >= 0.80 at 32K/64K at U_P in all five replicates (both panels)."""
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
    if any(all(c == NOT_LOADED for c in cs) for cs in per.values()):
        return NOT_TESTED_BY_LOAD
    if all(any(c in (NO_GAIN, REVERSED) for c in cs) for cs in per.values()) and not any(has_step.values()):
        return CAPACITY_NOT_SUPPORTED
    return INTERMEDIATE


# --- control and cost labels (section 8.5) --------------------------------------------------------------------------------------------------
class DenseCell(NamedTuple):
    """One CAPACITY STEP's larger cell against D-OQ, per replicate: for each of the three readings and each panel, (d, r, dense_a_use) where d = i(arm) - i(D-OQ) and
    r = I_use ratio (None when the denominator is zero; r with a zero denominator counts as at least 1.10)."""

    step: str
    replicates: list[dict[str, dict[str, tuple[float, float | None, float]]]]  # replicate -> reading -> panel -> (d, r, dense a_use)


def dense_reading(i_arm: float, i_dense: float, n: int) -> tuple[float, float | None]:
    """d = i(arm) - i(D-OQ) and r = I_use(arm) / I_use(D-OQ) (None for a zero denominator)."""
    d = i_arm - i_dense
    r = None if i_dense <= 0.0 else i_arm / i_dense  # same facts in both: the ratio of I_use is the ratio of i
    return d, r


def dense_label(cells: Sequence[DenseCell], missing_dense: Sequence[str] = ()) -> dict[str, Any]:
    """Dense label of an arm over the larger cells of its CAPACITY STEPs (section 8.5): DENSE AHEAD (d at most -0.25 in at least 4 replicates, in any one reading, at any such
    cell) takes precedence; BEATS DENSE (r at least 1.10 in all 5, under MU and under MC, on both panels, at every such cell); DENSE MATCHES otherwise. A cell with no D-OQ
    read is DENSE NOT READ. Returns the label, the reason and D-OQ's a_use at each cell in each reading."""
    detail: dict[str, Any] = {"cells": {}}
    if not cells:
        return {"label": DENSE_NOT_READ, "detail": detail, "missing": list(missing_dense)}
    ahead_any = False
    beats_all = True
    dense_at_chance_cells: list[str] = []
    for cell in cells:
        info: dict[str, Any] = {}
        for reading in ("MU", "MC", "D-BEST"):
            n_ahead = sum(1 for rep in cell.replicates if all(le(rep[reading][p][0], core.DENSE_AHEAD_BITS) for p in core.PANELS))
            info[reading] = {"replicates_ahead": n_ahead, "dense_a_use": [[rep[reading][p][2] for p in core.PANELS] for rep in cell.replicates]}
            ahead_any = ahead_any or n_ahead >= core.PAIRED_MOST
        for reading in ("MU", "MC"):
            for rep in cell.replicates:
                for p in core.PANELS:
                    _, r, dense_a = rep[reading][p]
                    if r is not None and not ge(r, core.BEATS_DENSE_RATIO):
                        beats_all = False
                    if r is None and cell.step not in dense_at_chance_cells:
                        dense_at_chance_cells.append(cell.step)
        detail["cells"][cell.step] = info
    if ahead_any:
        return {"label": DENSE_AHEAD, "detail": detail, "missing": list(missing_dense)}
    if beats_all:
        label = BEATS_DENSE if not dense_at_chance_cells else f"{BEATS_DENSE} (DENSE AT CHANCE AT {', '.join(dense_at_chance_cells)})"
        return {"label": label, "detail": detail, "missing": list(missing_dense)}
    return {"label": DENSE_MATCHES, "detail": detail, "missing": list(missing_dense)}


def active_work_label(w_small: float, w_large: float) -> str:
    """SUBLINEAR if W at most doubles across the fourfold step, else LINEAR KEY SCORING (section 7.4 item 2)."""
    return SUBLINEAR if le(w_large, core.SUBLINEAR_FACTOR * w_small) else LINEAR_KEY_SCORING


def hierarchy_label(ratios: Sequence[Mapping[str, Mapping[str, float]]]) -> str:
    """T-OQ against F-OQ-IVF on I_use at 8K/16K and 32K/64K at U_P (section 8.5): ``ratios[replicate][cell][panel]`` = I_use(T-OQ) / I_use(F-OQ-IVF). TREE_AHEAD if the ratio is
    at least 1.03 in at least 4 replicates at both cells; TREE_COMPETITIVE if at least 0.97 in at least 4 at both cells; otherwise TREE_BEHIND."""
    cells = sorted({c for rep in ratios for c in rep})

    def count(threshold: float, cell: str) -> int:
        return sum(1 for rep in ratios if cell in rep and all(ge(rep[cell][p], threshold) for p in core.PANELS))

    if cells and all(count(core.TREE_AHEAD_RATIO, c) >= core.PAIRED_MOST for c in cells):
        return TREE_AHEAD
    if cells and all(count(core.TREE_COMPETITIVE_RATIO, c) >= core.PAIRED_MOST for c in cells):
        return TREE_COMPETITIVE
    return TREE_BEHIND


def conventional_suffices(i_arm: Sequence[Mapping[str, float]], i_knn: Sequence[Mapping[str, float]], i_knn_ivf: Sequence[Mapping[str, float]]) -> bool:
    """CONVENTIONAL RETRIEVAL SUFFICES if KNN-W's or KNN-W-IVF's i is within 0.25 of the arm's, or above it, on both panels in at least 4 replicates at 32K/64K. Each argument is
    per replicate: panel -> i."""
    count = 0
    for arm, k, kv in zip(i_arm, i_knn, i_knn_ivf, strict=True):
        if any(all(ge(c[p], arm[p] - core.CONVENTIONAL_WITHIN) for p in core.PANELS) for c in (k, kv)):
            count += 1
    return count >= core.PAIRED_MOST


def key_learning_limited(h8_class: str, foq_class: str) -> bool:
    return h8_class == CAPACITY_SUPPORTED and foq_class != CAPACITY_SUPPORTED


# --- descriptive labels (section 8.6) ---------------------------------------------------------------------------------------------------------
def study_b_label(per_replicate: Sequence[Mapping[str, Mapping[str, Sequence[tuple[float, float, float, float] | None]]]], work_sublinear: bool, memory_attributed: Sequence[bool]) -> dict[str, Any]:
    """Study B per arm (section 8.6). ``per_replicate[r][reading][panel]`` holds, for the two diagonal steps (2K/4K to 8K/16K, 8K/16K to 32K/64K), the tuple
    ``(a_use small, a_use large, i small, i large)`` read at the reading (MU: both cells at U_P; MC: the pair's matched readouts) or None where the reading is not established
    (MC-SHORT). KNOWLEDGE SCALES WITH MEMORY needs, in all 5 replicates, on both panels, under MU and under MC separately: a_use at least 0.85 at every diagonal cell, I_use growing
    at least 3.0 times at both diagonal steps, both steps MEMORY-ATTRIBUTED (the off-diagonal step A1, B2 is a CAPACITY STEP) and sublinear counted work. KNOWLEDGE DOES NOT SCALE if
    a_use < 0.5 at the largest diagonal cell in at least 4 replicates. A ratio is computed only when both cells have a_use >= 0.5 (else NOT ASSESSED)."""
    scale_all = work_sublinear and all(memory_attributed) and len(per_replicate) == core.REPLICATES
    not_assessed = False
    for rep in per_replicate:
        for reading in ("MU", "MC"):
            for p in core.PANELS:
                steps = rep[reading][p]
                for step in steps:
                    if step is None:
                        scale_all = False
                        continue
                    a_s, a_l, i_s, i_l = step
                    if not (ge(a_s, core.STUDY_B_A_USE) and ge(a_l, core.STUDY_B_A_USE)):
                        scale_all = False
                    if lt(a_s, core.NOT_ASSESSED_A_USE) or lt(a_l, core.NOT_ASSESSED_A_USE):
                        not_assessed = True
                        scale_all = False
                    elif not (i_s > 0 and ge(i_l / i_s, core.STUDY_B_RATIO)):
                        scale_all = False

    def below(rep: Mapping[str, Mapping[str, Sequence[tuple[float, float, float, float] | None]]]) -> bool:
        vals = [steps[1][1] for reading in ("MU", "MC") for steps in rep[reading].values() if steps[1] is not None]
        return bool(vals) and all(lt(a_use, core.NOT_ASSESSED_A_USE) for a_use in vals)

    n_below = sum(1 for rep in per_replicate if below(rep))
    if scale_all:
        label = SCALES
    elif n_below >= core.PAIRED_MOST:
        label = DOES_NOT_SCALE
    else:
        label = NOT_ESTABLISHED
    return {"label": label, "ratio_not_assessed": not_assessed, "replicates_below_0_5_at_largest": n_below}


def robustness_label(rises: Sequence[float]) -> str:
    """Per step, cells with a_use >= 0.5, accuracy retained under 20% slot dropout: ``rises`` (larger minus smaller, one per replicate). RISES WITH SLOTS if >= 0.05 in all 5, FALLS
    if it drops by >= 0.05 in at least 4, UNCHANGED otherwise."""
    if len(rises) == core.REPLICATES and all(ge(r, core.ROBUSTNESS_RISE) for r in rises):
        return "RISES WITH SLOTS"
    if sum(1 for r in rises if le(r, -core.ROBUSTNESS_RISE)) >= core.PAIRED_MOST:
        return "FALLS"
    return "UNCHANGED"


def held_out_fragile(arm_ratio: float, r2_ratio: float) -> bool:
    """HELD-OUT FRAGILE: the arm's ratio of H1 (or H2) accuracy to Panel A accuracy below 0.90 x the same ratio for R2 of the same replicate at the row's reference cell."""
    return lt(arm_ratio, core.HELDOUT_FRAGILE * r2_ratio)


# --- capacity outcome (section 8.7) --------------------------------------------------------------------------------------------------------------
@dataclass
class ArmCapacity:
    arm: str
    cls: str
    dense: str  # the dense label (DENSE_AHEAD, BEATS_DENSE..., DENSE_MATCHES, DENSE_NOT_READ)
    capacity_steps: list[str] = field(default_factory=list)
    dense_text: str = ""


class Outcome(NamedTuple):
    row: int
    label: str
    reasons: list[str]
    printed: str


def _is_ahead(a: ArmCapacity) -> bool:
    return a.dense == DENSE_AHEAD


def capacity_outcome(
    arms: Mapping[str, ArmCapacity],
    *,
    engineering_failed: bool,
    incomplete: bool,
    no_loaded_directed: bool = False,
    every_step_not_loaded: bool = False,
    reasons_extra: Sequence[str] = (),
    printed_details: Sequence[str] = (),
) -> Outcome:
    """The capacity outcome (section 8.7, first match wins). CAPACITY-POSITIVE: F-OQ, T-OQ or F-OQ-IVF is CAPACITY_SUPPORTED and is not DENSE AHEAD; an arm whose CAPACITY STEP
    has no D-OQ read cannot by itself support CAPACITY_SUPPORTED (DENSE NOT READ). CAPACITY-NEGATIVE: (a) F-OQ and T-OQ are both CAPACITY_NOT_SUPPORTED; or (b) at least one of
    F-OQ, T-OQ, F-OQ-IVF is CAPACITY_SUPPORTED and every such arm is DENSE AHEAD (an empty set never satisfies (b)). NOT TESTED: for F-OQ and T-OQ every step is NOT LOADED, or the
    human lead directed it in the freeze record. Otherwise CAPACITY-INCONCLUSIVE with the reasons."""
    if engineering_failed:
        return Outcome(1, S1_ENGINEERING_FAILURE, ["an engineering gate failed or frozen and running identities differ"], S1_ENGINEERING_FAILURE + " (no scientific label on either line)")
    if incomplete:
        return Outcome(2, S1_INCOMPLETE, ["a registered cell lacks a record"], S1_INCOMPLETE + " (status; no outcome on either line)")
    learned = [arms[a] for a in core.LEARNED_KEY_ARMS if a in arms]
    supported = [a for a in learned if a.cls == CAPACITY_SUPPORTED]
    positive = [a for a in supported if a.dense not in (DENSE_AHEAD, DENSE_NOT_READ)]
    if positive:
        names = ", ".join(a.arm for a in positive)
        details = [f"arm(s) {names}", *[f"{a.arm}: {a.dense}" + (f" ({a.dense_text})" if a.dense_text else "") for a in positive], *printed_details]
        return Outcome(3, CAPACITY_POSITIVE, [], emit(tagged(CAPACITY_POSITIVE, "WITHIN REGISTERED RUN LENGTHS", *details)))
    foq, toq = arms.get("F-OQ"), arms.get("T-OQ")
    if foq is not None and toq is not None and foq.cls == CAPACITY_NOT_SUPPORTED and toq.cls == CAPACITY_NOT_SUPPORTED:
        return Outcome(4, CAPACITY_NEGATIVE, ["(a) F-OQ and T-OQ are both CAPACITY_NOT_SUPPORTED"], f"{CAPACITY_NEGATIVE} (a)")
    if supported and all(_is_ahead(a) for a in supported):
        return Outcome(4, CAPACITY_NEGATIVE, ["(b) every CAPACITY_SUPPORTED arm is DENSE AHEAD"], f"{CAPACITY_NEGATIVE} (b: DENSE AHEAD)")
    if no_loaded_directed or every_step_not_loaded:
        return Outcome(5, CAPACITY_NOT_TESTED, ["no loaded cell within budget"], CAPACITY_NOT_TESTED)
    reasons = list(reasons_extra) or [f"{a.arm}: {a.cls}" for a in learned]
    if any(a.cls == CAPACITY_SUPPORTED and a.dense == DENSE_NOT_READ for a in learned):
        reasons.append("a CAPACITY_SUPPORTED arm has no D-OQ read at its CAPACITY STEP (DENSE NOT READ)")
    return Outcome(6, CAPACITY_INCONCLUSIVE, reasons, tag_positives(f"{CAPACITY_INCONCLUSIVE}: " + "; ".join(reasons)))


def milestone_reading(outcome: Outcome, arms: Mapping[str, ArmCapacity], work: Mapping[str, str], hierarchy: str, s0_status: str) -> str:
    """The reading for milestone question 1 on the capacity line only (section 8.7), always printed with S0's status line."""
    suffix = f" | {s0_status} | {core.ORACLE_SENTENCE}"
    if outcome.label == CAPACITY_POSITIVE:
        sub = [a for a in ("T-OQ", "F-OQ-IVF") if a in arms and arms[a].cls == CAPACITY_SUPPORTED and arms[a].dense not in (DENSE_AHEAD, DENSE_NOT_READ) and work.get(a) == SUBLINEAR]
        if sub:
            return emit(tagged("Storage half supported, as a necessary condition", f"arm {sub[0]}", f"hierarchy label {hierarchy}", "says nothing about addressing by the model, use of the store by a language model, or capability beyond recall of the trained facts")) + suffix
        return emit(tagged("Capacity shown; sublinear active work not shown")) + suffix
    if outcome.label == CAPACITY_NEGATIVE:
        return "Storage half not supported for this store, backbone, task and budget" + suffix
    return ("Not tested" if outcome.label == CAPACITY_NOT_TESTED else "Not established") + suffix


# --- efficiency line (section 8.8) -------------------------------------------------------------------------------------------------------------------
class UT(NamedTuple):
    """u_T of a cell: exact (``lo`` = ``hi`` = u), left-censored (in (0, s_hit]) or right-censored (above U_run)."""

    kind: str  # "exact", "left", "right"
    lo: float
    hi: float

    @property
    def censored(self) -> bool:
        return self.kind != "exact"


class UTResult(NamedTuple):
    ut: UT
    dep_failed: bool
    s_hit: int | None
    s_prev: int | None


def u_t(views: Sequence[View]) -> UTResult:
    """u_T (section 8.8): at each snapshot the cell qualifies if i >= 3.0 on both panels and DEP passes; s_hit is the first qualifying snapshot (a first snapshot with i >= i_T on
    both panels at which DEP fails is DEPENDENCE_FAILED), s_prev the one before it; u_T is found by linear interpolation of the minimum of the two panels' i against log2(updates)
    between them; left-censored in (0, s_hit] if s_hit is the first snapshot; right-censored above U_run if none qualifies."""
    ups = sorted(set.intersection(*(set(v.updates) for v in views)))
    run = views[0].run
    for k, s in enumerate(ups):
        if all(ge(v.i(s), core.EFFICIENCY_I_T) for v in views):
            if any(v.dep(s) is False for v in views):
                return UTResult(UT("right", float(run), math.inf), True, s, ups[k - 1] if k else None)
            if k == 0:
                return UTResult(UT("left", 0.0, float(s)), False, s, None)
            prev = ups[k - 1]
            m_prev, m_hit = min(v.i(prev) for v in views), min(v.i(s) for v in views)
            frac = (core.EFFICIENCY_I_T - m_prev) / (m_hit - m_prev) if m_hit > m_prev else 1.0
            x = math.log2(prev) + max(0.0, min(1.0, frac)) * (math.log2(s) - math.log2(prev))
            value = 2.0**x
            return UTResult(UT("exact", value, value), False, s, prev)
    return UTResult(UT("right", float(run), math.inf), False, None, None)


class EffStep(NamedTuple):
    verdict: str
    detail: dict[str, Any]


REACHED_ONLY, FASTER, FASTER_UPDATES_ONLY, SLOWER, SAME = "REACHED ONLY BY THE LARGER", "FASTER", "FASTER IN UPDATES ONLY", "SLOWER", "SAME"


def efficiency_step(
    small: UTResult,
    large: UTResult,
    *,
    ref_ok: bool,
    leakage: bool,
    run_small: int,
    run_large: int,
    cost_small: Mapping[str, float],
    cost_large: Mapping[str, float],
) -> EffStep:
    """Efficiency step verdict of one replicate (rows 1 to 8 of section 8.8, first match wins). A condition on a censored value holds only if it holds for every value the bounds
    allow. ``cost_*`` are the frozen costs per update (``cpu`` and ``madds``), so c_T = u_T x cost per update in each measure."""
    d: dict[str, Any] = {"u_t_small": [small.ut.kind, small.ut.lo, small.ut.hi], "u_t_large": [large.ut.kind, large.ut.lo, large.ut.hi]}
    if not ref_ok or leakage:
        return EffStep(NOT_EVALUATED, {**d, "reason": "REF failed" if not ref_ok else "LEAKAGE"})
    if small.dep_failed or large.dep_failed:
        return EffStep(DEPENDENCE_FAILED, d)
    xs, ys = large.ut, small.ut  # x: larger cell (4N), y: smaller cell (N)
    measures = ("cpu", "madds")

    def half_updates() -> bool:  # u_T(4N) <= u_T(N) / 2 for every value
        return le(xs.hi, ys.lo / 2.0)

    def half_cost() -> bool:  # c_T(4N) <= 0.8 c_T(N) in both measures
        return all(le(xs.hi * cost_large[m], core.EFFICIENCY_COST_FACTOR * ys.lo * cost_small[m]) for m in measures)

    row4 = ys.kind == "right" and le(xs.hi, run_small / 2.0) and all(le(xs.hi * cost_large[m], core.EFFICIENCY_COST_FACTOR * run_small * cost_small[m]) for m in measures)
    row5 = half_updates() and half_cost()
    row6 = half_updates()
    larger_right_ok = xs.kind != "right" or run_large >= 2.0 * ys.hi
    row7 = ge(xs.lo, 2.0 * ys.hi) and math.isfinite(ys.hi) and larger_right_ok
    if (small.ut.kind == "right" and large.ut.kind == "right") or (small.ut.censored or large.ut.censored) and not (row4 or row5 or row6 or row7):
        return EffStep(NOT_ASSESSED, d)
    if row4:
        return EffStep(REACHED_ONLY, d)
    if row5:
        return EffStep(FASTER, d)
    if row6:
        return EffStep(FASTER_UPDATES_ONLY, d)
    if row7:
        return EffStep(SLOWER, d)
    return EffStep(SAME, d)


def efficiency_step_class(verdicts: Sequence[str]) -> str:
    """Step class (section 8.8, first match wins): NOT_EVALUATED (at least 2), DEPENDENCE_FAILED (at least 2), NOT_ASSESSED (at least 2), FASTER STEP (FASTER or REACHED ONLY BY
    THE LARGER in all 5), UPDATES-ONLY STEP (FASTER or FASTER IN UPDATES ONLY in all 5), SLOWER STEP (SLOWER in at least 4), NO DIFFERENCE (SAME in at least 4), MIXED."""
    if len(verdicts) != core.REPLICATES:
        raise ValueError("a step class needs one verdict per replicate")
    c = Counter(verdicts)
    n = len(verdicts)
    if c[NOT_EVALUATED] >= 2:
        return NOT_EVALUATED
    if c[DEPENDENCE_FAILED] >= 2:
        return DEPENDENCE_FAILED
    if c[NOT_ASSESSED] >= 2:
        return NOT_ASSESSED
    if c[FASTER] + c[REACHED_ONLY] == n:
        return "FASTER STEP"
    if c[FASTER] + c[FASTER_UPDATES_ONLY] == n:
        return "UPDATES-ONLY STEP"
    if c[SLOWER] >= core.PAIRED_MOST:
        return "SLOWER STEP"
    if c[SAME] >= core.PAIRED_MOST:
        return "NO DIFFERENCE"
    return MIXED


def efficiency_arm_class(step_classes: Mapping[str, str], transitions: Mapping[str, Sequence[str]]) -> str:
    """Arm class (F-OQ, T-OQ; section 8.8, first match wins)."""
    per = {t: [step_classes[s] for s in steps] for t, steps in transitions.items()}
    if any(all(c in (NOT_EVALUATED, NOT_ASSESSED) for c in cs) for cs in per.values()):
        return NOT_EVALUATED
    if any(c == DEPENDENCE_FAILED for c in step_classes.values()):
        return DEPENDENCE_FAILED
    faster = {t: any(c == "FASTER STEP" for c in cs) for t, cs in per.items()}
    if all(faster.values()) and not any(c == "SLOWER STEP" for c in step_classes.values()):
        return "EFFICIENCY_SUPPORTED"
    if any(faster.values()):
        return "EFFICIENCY_ONE_TRANSITION"
    if all(any(c in ("SLOWER STEP", "NO DIFFERENCE") for c in cs) for cs in per.values()) and not any(faster.values()):
        return "EFFICIENCY_NOT_SUPPORTED"
    return INTERMEDIATE


def dense_faster(arm_ut: Sequence[UT], dense_ut: Sequence[UT | None], cost_arm: Mapping[str, float], cost_dense: Mapping[str, float]) -> str:
    """At the larger cell of a FASTER STEP: DENSE FASTER if D-OQ's c_T is at most 0.8 of the arm's, in both cost measures, in at least 4 replicates (for every value the bounds allow);
    DENSE NOT READ if there is no D-OQ cell; otherwise DENSE NOT FASTER."""
    if any(d is None for d in dense_ut):
        return DENSE_NOT_READ
    n = sum(1 for a, d in zip(arm_ut, dense_ut, strict=True) if d is not None and all(le(d.hi * cost_dense[m], core.DENSE_FASTER_COST * a.lo * cost_arm[m]) for m in ("cpu", "madds")))
    return "DENSE FASTER" if n >= core.PAIRED_MOST else "DENSE NOT FASTER"


def efficiency_outcome(arm_classes: Mapping[str, str], dense: Mapping[str, str], *, engineering_failed: bool, incomplete: bool, details: Sequence[str] = ()) -> Outcome:
    """Efficiency outcome (section 8.8; rows 1 and 2 of section 8.7 apply first). EFFICIENCY-POSITIVE: F-OQ or T-OQ is EFFICIENCY_SUPPORTED and is not DENSE FASTER.
    EFFICIENCY-NEGATIVE: F-OQ and T-OQ are both EFFICIENCY_NOT_SUPPORTED; or at least one is EFFICIENCY_SUPPORTED and every such arm is DENSE FASTER (an empty set never
    satisfies the second clause). Otherwise EFFICIENCY-INCONCLUSIVE with the reason."""
    if engineering_failed:
        return Outcome(1, S1_ENGINEERING_FAILURE, ["an engineering gate failed or frozen and running identities differ"], S1_ENGINEERING_FAILURE + " (no scientific label on either line)")
    if incomplete:
        return Outcome(2, S1_INCOMPLETE, ["a registered cell lacks a record"], S1_INCOMPLETE + " (status; no outcome on either line)")
    supported = [a for a in core.EFFICIENCY_ARMS if arm_classes.get(a) == "EFFICIENCY_SUPPORTED"]
    ok = [a for a in supported if dense.get(a) != "DENSE FASTER"]
    if ok:
        return Outcome(3, EFFICIENCY_POSITIVE, [], emit(tagged(EFFICIENCY_POSITIVE, f"arm(s) {', '.join(ok)}", *[f"{a}: {dense.get(a, DENSE_NOT_READ)}" for a in ok], *details)))
    if all(arm_classes.get(a) == "EFFICIENCY_NOT_SUPPORTED" for a in core.EFFICIENCY_ARMS):
        return Outcome(4, EFFICIENCY_NEGATIVE, ["F-OQ and T-OQ are both EFFICIENCY_NOT_SUPPORTED"], EFFICIENCY_NEGATIVE)
    if supported and all(dense.get(a) == "DENSE FASTER" for a in supported):
        return Outcome(4, EFFICIENCY_NEGATIVE, ["every EFFICIENCY_SUPPORTED arm is DENSE FASTER"], EFFICIENCY_NEGATIVE + " (DENSE FASTER)")
    reasons = [f"{a}: {arm_classes.get(a, 'none')}" for a in core.EFFICIENCY_ARMS]
    return Outcome(5, EFFICIENCY_INCONCLUSIVE, reasons, tag_positives(f"{EFFICIENCY_INCONCLUSIVE}: " + "; ".join(reasons)))


def optimizer_assisted(share_small: float, share_large: float) -> bool:
    """The larger cell's share of value-row movement on updates without gradient exceeds the smaller cell's by more than 1.5 times."""
    return share_small > 0 and gt(share_large / share_small, core.OPTIMIZER_ASSISTED_RATIO)


def movement_ratios(small: Mapping[str, float], large: Mapping[str, float]) -> dict[str, float | None]:
    """The row-movement ratios printed with every budget and efficiency verdict (larger over smaller): total movement, movement without own gradient, and the share ratio."""

    def ratio(a: float, b: float) -> float | None:
        return None if b <= 0 else a / b

    return {
        "total": ratio(large["total"], small["total"]), "without_own_gradient": ratio(large["without_own_gradient"], small["without_own_gradient"]),
        "share_without": ratio(large["share_without"], small["share_without"]),
    }  # fmt: skip


def dedupe(items: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(items))
