# ruff: noqa: E501
"""P10S1 verdicts, classes, labels and outcomes (ADR-0021 sections 7 and 8): pure functions of counts and frozen tables, no I/O.

* capacity line: the step verdict of one replicate (8.2), the step class over five replicates (8.3), the arm class (8.4), the control and cost labels (8.5), the descriptive
  labels (8.6) and the capacity outcome (8.7);
* efficiency line: u_T with its censoring, the step verdict (8.8), the step class, the arm class, the dense label and the efficiency outcome;
* the saturation line (revision 5, section 8.10): the pair verdict, the pair class, the arm class and the outcome, and the dense label at saturation (section 8.5);
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
# saturation line (section 8.10)
NOT_FULL, PROPORTIONAL, SUBPROPORTIONAL = "NOT FULL", "PROPORTIONAL", "SUBPROPORTIONAL"
PROPORTIONAL_STEP, SUBPROPORTIONAL_STEP = "PROPORTIONAL STEP", "SUBPROPORTIONAL STEP"
SAT_NOT_MEASURED, SAT_DOES_NOT_SCALE, SAT_PROPORTIONAL_ALL_PAIRS = "SATURATION_NOT_MEASURED", "SATURATION_DOES_NOT_SCALE", "SATURATION_PROPORTIONAL_ALL_PAIRS"
SAT_PROPORTIONAL, SAT_SUBPROPORTIONAL, SAT_NOT_MEASURED_OUTCOME, SAT_INCONCLUSIVE = "SATURATION-PROPORTIONAL", "SATURATION-SUBPROPORTIONAL", "SATURATION NOT MEASURED", "SATURATION-INCONCLUSIVE"
DENSE_HOLDS_MORE, STORE_HOLDS_MORE, SAME_AT_SATURATION = "DENSE HOLDS MORE AT SATURATION", "STORE HOLDS MORE AT SATURATION", "SAME AT SATURATION"
DENSE_STILL_RISING, DENSE_NOT_LEARNED = "DENSE STILL RISING", "DENSE NOT LEARNED"
FLAT_BELOW_FLOOR, RISING, PLATEAUED = "FLAT BELOW THE DEP FLOOR", "STILL RISING", "PLATEAUED"
NOT_TESTED_16K_65K = "16,384→65,536 NOT TESTED"
NOT_FUNDED_16K = "16,384 NOT MEASURED — NOT FUNDED"
NOT_MEASURED_256 = "256 NOT MEASURED — NOT FULL WITHIN CEILING"
SIZES_EFFICIENCY = "SIZES 1,024–16,384"
SIZES_CAPACITY = "1,024 TO 16,384 SLOTS"
SAT_FIXED_PHRASES = ("EIGHT FACTS PER SLOT", "FULL = PLATEAU RULE WITHIN REGISTERED RUN LENGTHS")
H8_NOT_CALIBRATED = "H8 NOT CALIBRATED AT"
UNDERTRAINED = "UNDERTRAINED-AT-U_P"

# --- the tag and the positive labels (section 3 item 4) -------------------------------------------------------------------------------
POSITIVE_LABELS = (
    "CAPACITY STEP", "CAPACITY_SUPPORTED", "CAPACITY-POSITIVE", "EFFICIENCY_SUPPORTED", "EFFICIENCY-POSITIVE", "BEATS DENSE", "KNOWLEDGE SCALES WITH MEMORY", "TREE_AHEAD",
    "Storage half supported, as a necessary condition, from 1,024 to 16,384 slots", "Storage half supported, as a necessary condition", "Capacity shown; sublinear active work not shown", "CAPACITY_ONE_TRANSITION", "EFFICIENCY_ONE_TRANSITION", "FASTER STEP",
    "FASTER IN UPDATES ONLY", "REACHED ONLY BY THE LARGER", "FASTER", "PROPORTIONAL STEP", "SATURATION_PROPORTIONAL_ALL_PAIRS", "SATURATION-PROPORTIONAL", "STORE HOLDS MORE AT SATURATION",
    "Capacity steps shown; proportional saturation not shown",
)  # fmt: skip
# a label may be followed by ONE parenthetical group (``BEATS DENSE (DENSE AT CHANCE AT 8K/16K)``) before its tag, and may be plural (``CAPACITY STEPS``); ``DENSE FASTER`` and
# ``DENSE NOT FASTER`` are blocking labels, not positive ones
_TAG_AFTER = re.compile(r"(?:\s*\([^)]*\))?\s*\[[^\]]*" + re.escape(core.STORE_ONLY_TAG))
_POSITIVE_RE = re.compile(r"(?<![\w-])(?<!DENSE )(?<!NOT )(" + "|".join(re.escape(p) for p in sorted(POSITIVE_LABELS, key=len, reverse=True)) + r")(?:s|S)?(?![\w-])")


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
    "panels": "RULED (ADR-0021 section 22 (h)): for a label that favours the store (TREE_AHEAD, TREE_COMPETITIVE and every positive condition) a replicate counts only if both panels satisfy it; for a label that blocks (DENSE AHEAD, DENSE FASTER) a replicate counts if either panel satisfies it; PANEL-DISAGREE is the verdict when the panels give different verdicts",
    "dep_reads": "RULED (section 22 (g)): DEP is read at every snapshot up to the run length, of both cells",
    "mc_direction": "RULED (section 22 (i)): the costlier cell of a pair is read at U_P and the cheaper at the smallest snapshot of the MC grid whose cumulative cost is at least that; the two cost measures giving different costlier cells is MC-AMBIGUOUS (not established)",
    "movement": "READING: the row-movement ratio printed with a verdict is the larger cell's total value-row movement over the smaller's at U_P, with the without-gradient share ratio beside it; OPTIMIZER-ASSISTED tests the share ratio; efficiency verdicts also print both at each cell's hit snapshot",
    "dense_not_established": "RULED (section 22 M5): where the dense matched-compute pair is MC-SHORT or MC-AMBIGUOUS the label is DENSE NOT ESTABLISHED AT MATCHED COMPUTE (<status>), never DENSE MATCHES; the matched-updates comparison with D-OQ is printed beside it, descriptively; as designed S1 cannot show that the store beats or matches a dense map at matched compute at 65,536 slots",
    "dense_efficiency": "RULED (section 22 (k), m3): a FASTER STEP with no D-OQ cell prints DENSE NOT READ, one whose dense-speed comparison is undecided from the bounds prints DENSE SPEED UNDECIDED; neither blocks",
    "analytic_madds": "RULED (section 22 M6): analytic multiply-adds are those of one whole training update including the frozen backbone's forward and backward pass (formula in the config, checked against a FLOP count by a test) plus 4 x trainable parameters for AdamW",
    "knn_information": "READING: i of KNN-W, KNN-W-IVF and DICT is computed from raw accuracy (there is no memory to swap)",
    "robustness": "RULED (section 22 (n)): robustness is read on Panel A and printed for both panels, accuracy retained = mean raw accuracy over three seeded masks; descriptive",
    "seed_block_readouts": "RULED (section 22 (m)): the seed block's spread is reported at U_P and U_run; descriptive",
    "dense_rate_tie": "RULED (section 22 M7): among dense rates within 0.02 at the selection readout, the faster learner (a_use at U_P/2, U_P/4, down to U_P/16; the first difference of at least 0.02 decides), else the smaller learning rate",
    "mc_snapshot_grid": "READING: a multiplier above 6 has no snapshot on the MC grid and is MC-SHORT",
    "simulation_setting": "RATIFIED (section 22 (c)): page misses at 8 rows per page, rho = 1/4, ascending tie rule; descriptive, enters no rule",
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

    def gain_flat(self) -> bool:
        """i*(c; U_run) - i*(c; U_run/2) at most 0.10 bits per fact."""
        return le(self.i_star(self.run)[0] - self.i_star(self.run // 2)[0], core.PLATEAU_MAX)

    def above_floor(self) -> bool:
        """i*(c; U_run/2) at least 0.473 bits per fact (a_use 0.25, the floor below which DEP is not evaluated); new in revision 5 (section 8.2)."""
        return ge(self.i_star(self.run // 2)[0], core.PLATEAU_FLOOR_I)

    def plateaued(self) -> bool:
        """The gain over the last doubling is at most 0.10 bits per fact AND i*(c; U_run/2) is at least the DEP floor (section 8.2, revision 5)."""
        return self.gain_flat() and self.above_floor()

    def plateau_status(self) -> str:
        """PLATEAUED; FLAT BELOW THE DEP FLOOR (the gain condition holds, the floor does not: not 'still improving'); STILL RISING (the gain condition fails)."""
        if not self.gain_flat():
            return RISING
        return PLATEAUED if self.above_floor() else FLAT_BELOW_FLOOR

    def loaded(self) -> bool:
        """Plateaued and i*(c; U_run) at most 4.0 bits per fact (section 8.2)."""
        return self.plateaued() and le(self.i_star(self.run)[0], core.LOADED_I_MAX)


# --- matched compute (section 5.4) --------------------------------------------------------------------------------------------------------
class McEntry(NamedTuple):
    """The MC readout of a pair of cells: the update of each cell's readout, or the status (MC-SHORT when the matching snapshot exceeds the other cell's run length or the multiplier is above the
    grid). ``annotation`` is MC-AMBIGUOUS when the two cost measures disagreed on the costlier cell and the pair was read in the comparator's favour (section 5.4, revision 5): the status is
    then "OK" and the pair counts as established."""

    status: str  # "OK" or MC_SHORT
    small_update: int | None
    large_update: int | None
    multiplier: float
    cheaper: str | None  # "small" or "large": the cell read at its matched snapshot
    annotation: str | None = None  # MC_AMBIGUOUS

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


def mc_pair(costs_small: Mapping[str, float], costs_large: Mapping[str, float], u_p: int, run_small: int, run_large: int, claim: str = "large") -> McEntry:
    """The MC readouts of a (smaller, larger) pair from the two frozen cost measures per update (``cpu`` seconds and ``madds``). The costlier cell is read at U_P, the cheaper at the
    smallest grid snapshot whose cumulative cost is at least the costlier cell's; the larger of the two multipliers is used. Equal costs (|r - 1| <= EPS in both measures) are not a disagreement.

    If the two measures disagree on which cell costs more, the pair is read in the comparator's favour (ADR-0021 section 5.4, revision 5; review M7): ``claim`` names the cell whose advantage
    would be claimed ("large" on the capacity line, "small" for the memory arm in the dense labels, where role small is the arm and role large is D-OQ). That cell is read at U_P and the other
    at the smallest grid snapshot whose multiplier is at least the largest of r and 1/r over both measures; the entry is "OK" with the annotation MC-AMBIGUOUS, or MC-SHORT if that snapshot
    exceeds the other cell's run length."""
    if claim not in ("small", "large"):
        raise ValueError("claim is 'small' or 'large'")
    ratios = {m: costs_large[m] / costs_small[m] for m in ("cpu", "madds")}
    large_costlier = [r >= 1.0 - EPS for r in ratios.values()]
    if all(large_costlier):
        status, update, mult = match_snapshot(list(ratios.values()), u_p, run_small)
        return McEntry(status, update, u_p if status == "OK" else None, mult, "small")
    if not any(r >= 1.0 + EPS for r in ratios.values()):
        status, update, mult = match_snapshot([1.0 / r for r in ratios.values()], u_p, run_large)
        return McEntry(status, u_p if status == "OK" else None, update, mult, "large")
    mult = max(max(r, 1.0 / r) for r in ratios.values())
    if claim == "large":  # the larger cell is read at U_P; the smaller at the later snapshot
        status, update, mult = match_snapshot([mult], u_p, run_small)
        return McEntry(status, update, u_p if status == "OK" else None, mult, "small", MC_AMBIGUOUS)
    status, update, mult = match_snapshot([mult], u_p, run_large)
    return McEntry(status, u_p if status == "OK" else None, update, mult, "large", MC_AMBIGUOUS)


# --- capacity line: step verdict of one replicate (section 8.2) ------------------------------------------------------------------------------
class StepResult(NamedTuple):
    verdict: str
    detail: dict[str, Any]


def _reads(small: View, large: View, mc: McEntry) -> tuple[set[int], set[int]]:
    """DEP is read at every snapshot up to the run length of both cells (ADR-0021 section 22 (g)); the MC readouts are snapshots of the series."""
    return set(small.updates), set(large.updates)


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
    d.update(smaller_loaded=loaded, smaller_plateaued=p_small, larger_plateaued=p_large, a_use_large_up=large.a_use(u_p), smaller_plateau_status=small.plateau_status(), larger_plateau_status=large.plateau_status())
    if FLAT_BELOW_FLOOR in (small.plateau_status(), large.plateau_status()):
        d["note"] = f"{FLAT_BELOW_FLOOR}: the gain over the last doubling is within 0.10 bits per fact but i* at half the run length is below {core.PLATEAU_FLOOR_I:.3f} bits per fact; not 'still improving'"
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
DENSE_NOT_ESTABLISHED = "DENSE NOT ESTABLISHED AT MATCHED COMPUTE"
DENSE_SPEED_UNDECIDED = "DENSE SPEED UNDECIDED"
DENSE_MATCHES_SENTENCE = "a dense map with the same parameters, input and compute retained as much; the memory did it with {w_arm} / {w_dense} of the counted work"


def dense_not_established(label: str) -> bool:
    return label.startswith(DENSE_NOT_ESTABLISHED)


class DenseCell(NamedTuple):
    """One CAPACITY STEP's larger cell against D-OQ, per replicate: for each reading (MU, MC where established, D-BEST) and each panel, (d, r, dense_a_use) where d = i(arm) - i(D-OQ)
    and r = I_use ratio (None when the denominator is zero; r with a zero denominator counts as at least 1.10). ``mc_status`` is "OK" or the status (MC-SHORT, MC-AMBIGUOUS) of the
    dense matched-compute pair; the MC reading is absent from ``replicates`` unless it is "OK"."""

    step: str
    replicates: list[dict[str, dict[str, tuple[float, float | None, float]]]]  # replicate -> reading -> panel -> (d, r, dense a_use)
    mc_status: str = "OK"
    mc_annotation: str | None = None  # MC-AMBIGUOUS: the cost measures disagreed and the pair was read in the comparator's favour (section 5.4)


def dense_reading(i_arm: float, i_dense: float, n: int) -> tuple[float, float | None]:
    """d = i(arm) - i(D-OQ) and r = I_use(arm) / I_use(D-OQ) (None for a zero denominator)."""
    d = i_arm - i_dense
    r = None if i_dense <= 0.0 else i_arm / i_dense  # same facts in both: the ratio of I_use is the ratio of i
    return d, r


def _range(values: Sequence[float]) -> str:
    finite = [v for v in values if math.isfinite(v)]
    return "n/a" if not finite else (f"{min(finite):+.2f}" if min(finite) == max(finite) else f"{min(finite):+.2f} to {max(finite):+.2f}")


def matched_updates_text(cell: DenseCell) -> str:
    """The matched-updates (MU) comparison with D-OQ, descriptive, with its sign and size (D-OQ then has at least the arm's compute): d in bits per fact and r over the replicates and panels."""
    d = [rep["MU"][p][0] for rep in cell.replicates for p in core.PANELS]
    r = [x for rep in cell.replicates for p in core.PANELS if (x := rep["MU"][p][1]) is not None]
    return f"{cell.step} matched updates (descriptive; D-OQ has at least the arm's compute): d = {_range(d)} bits per fact, r = {'n/a' if not r else f'{min(r):.2f} to {max(r):.2f}'}"


def dense_label(cells: Sequence[DenseCell], missing_dense: Sequence[str] = ()) -> dict[str, Any]:
    """Dense label of an arm over the larger cells of its CAPACITY STEPs (section 8.5, with the lead's rulings of section 22). DENSE AHEAD (d at most -0.25 in at least 4 replicates, in any
    one established reading, at any such cell; a blocking label: a replicate counts if EITHER panel satisfies it) takes precedence. Where a cell's dense matched-compute pair is not
    established (MC-SHORT, MC-AMBIGUOUS) the label is DENSE NOT ESTABLISHED AT MATCHED COMPUTE (<status>), never DENSE MATCHES or BEATS DENSE, with the matched-updates comparison printed
    beside it. BEATS DENSE (r at least 1.10 in all 5, under MU and under MC, on both panels, at every such cell) and DENSE MATCHES need every cell established. A cell with no D-OQ read is
    DENSE NOT READ. Returns the label, the reason, D-OQ's a_use at each cell in each reading and the matched-updates text."""
    detail: dict[str, Any] = {"cells": {}}
    if not cells:
        return {"label": DENSE_NOT_READ, "detail": detail, "missing": list(missing_dense), "mu_text": []}
    ahead_any = False
    beats_all = True
    dense_at_chance_cells: list[str] = []
    statuses: list[str] = []
    for cell in cells:
        info: dict[str, Any] = {}
        readings = ("MU", "MC", "D-BEST") if cell.mc_status == "OK" else ("MU", "D-BEST")
        if cell.mc_status != "OK":
            statuses.append(cell.mc_status)
        for reading in readings:
            n_ahead = sum(1 for rep in cell.replicates if any(le(rep[reading][p][0], core.DENSE_AHEAD_BITS) for p in core.PANELS))
            info[reading] = {"replicates_ahead": n_ahead, "dense_a_use": [[rep[reading][p][2] for p in core.PANELS] for rep in cell.replicates]}
            ahead_any = ahead_any or n_ahead >= core.PAIRED_MOST
        for reading in ("MU", "MC"):
            if reading not in readings:
                beats_all = False
                continue
            for rep in cell.replicates:
                for p in core.PANELS:
                    _, r, _dense_a = rep[reading][p]
                    if r is not None and not ge(r, core.BEATS_DENSE_RATIO):
                        beats_all = False
                    if r is None and cell.step not in dense_at_chance_cells:
                        dense_at_chance_cells.append(cell.step)
        detail["cells"][cell.step] = info
    out = {"detail": detail, "missing": list(missing_dense), "mu_text": [matched_updates_text(c) for c in cells], "mc_statuses": statuses, "mc_ambiguous": [c.step for c in cells if c.mc_annotation]}
    if ahead_any:
        return {"label": DENSE_AHEAD, **out}
    if statuses:
        return {"label": f"{DENSE_NOT_ESTABLISHED} ({', '.join(dict.fromkeys(statuses))})", **out}
    if beats_all:
        label = BEATS_DENSE if not dense_at_chance_cells else f"{BEATS_DENSE} (DENSE AT CHANCE AT {', '.join(dense_at_chance_cells)})"
        return {"label": label, **out}
    return {"label": DENSE_MATCHES, **out}


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


# --- descriptive labels (section 8.6); Study B's label is retired: the saturation line (section 8.10) replaces it ---------------------------------------
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


# --- dense at saturation (section 8.5, revision 5) ----------------------------------------------------------------------------------------------
class SatDenseCell(NamedTuple):
    """One loaded cell (8K/1K or 32K/4K), the arm and D-OQ both read at the cell's run length U_L. ``replicates[r][panel]`` = (d_sat, r_sat) with d_sat = i*(arm; U_L) - i*(D-OQ; U_L) and
    r_sat = F i*(arm) / F i*(D-OQ) (None when D-OQ's i* is zero); ``dense_status[r][panel]`` is D-OQ's plateau status at U_L (``View.plateau_status``); ``cost_ok`` is True when D-OQ's cost per
    update is at least the arm's in both cost measures (section 5.4)."""

    cell: str
    replicates: list[dict[str, tuple[float, float | None]]]
    dense_status: list[dict[str, str]]
    cost_ok: bool


def dense_at_saturation(cells: Sequence[SatDenseCell]) -> dict[str, Any]:
    """The dense label at saturation (section 8.5; first match wins). DENSE HOLDS MORE AT SATURATION: d_sat at most -0.25 in at least 4 replicates (a replicate counts if EITHER panel satisfies it,
    section 22 (h)), at any loaded cell. STORE HOLDS MORE AT SATURATION: r_sat at least 1.10 in all 5 replicates on both panels at every loaded cell, D-OQ plateaued (section 8.2) at each in all 5,
    and D-OQ's cost per update at least the arm's in both measures. SAME AT SATURATION otherwise; where row 2 fails only because D-OQ is not plateaued the sub-label is DENSE STILL RISING (some view
    still gains), or DENSE NOT LEARNED (every failing view is flat below the DEP floor); where it fails only on the cost condition, DENSE NOT ESTABLISHED AT MATCHED COMPUTE. Where two of the
    three conditions fail, no sub-label is chosen between them: the labels of every failing condition that would have been the only one are not printed, and the failing conditions are listed."""
    if not cells:
        return {"label": SAME_AT_SATURATION, "sublabels": [], "failing": ["no loaded cell read"], "detail": {}}
    ahead = any(sum(1 for rep in c.replicates if any(le(d, core.DENSE_AHEAD_BITS) for d, _r in rep.values())) >= core.PAIRED_MOST for c in cells)
    detail: dict[str, Any] = {c.cell: {"d_sat": [{p: v[0] for p, v in rep.items()} for rep in c.replicates], "r_sat": [{p: v[1] for p, v in rep.items()} for rep in c.replicates], "dense_status": c.dense_status, "cost_ok": c.cost_ok} for c in cells}
    if ahead:
        return {"label": DENSE_HOLDS_MORE, "sublabels": [], "failing": [], "detail": detail}
    ratio_ok = all(len(c.replicates) == core.REPLICATES and all(r is None or ge(r, core.BEATS_DENSE_RATIO) for rep in c.replicates for _d, r in rep.values()) for c in cells)
    statuses = [st for c in cells for rep in c.dense_status for st in rep.values()]
    plateau_ok = all(st == PLATEAUED for st in statuses) and all(len(c.dense_status) == core.REPLICATES for c in cells)
    cost_ok = all(c.cost_ok for c in cells)
    if ratio_ok and plateau_ok and cost_ok:
        return {"label": STORE_HOLDS_MORE, "sublabels": [], "failing": [], "detail": detail}
    failing = [name for name, ok in (("ratio", ratio_ok), ("dense plateau", plateau_ok), ("cost", cost_ok)) if not ok]
    sub: list[str] = []
    if failing == ["dense plateau"]:
        sub = [DENSE_STILL_RISING if RISING in statuses else DENSE_NOT_LEARNED]
    elif failing == ["cost"]:
        sub = [DENSE_NOT_ESTABLISHED]
    elif ratio_ok:  # the ratio holds and both of the other conditions fail: both sub-labels apply (the conservative reading)
        sub = [DENSE_STILL_RISING if RISING in statuses else DENSE_NOT_LEARNED, DENSE_NOT_ESTABLISHED]
    return {"label": SAME_AT_SATURATION, "sublabels": sub, "failing": failing, "detail": detail}


# --- saturation line (section 8.10, revision 5) ---------------------------------------------------------------------------------------------------
class SatSide(NamedTuple):
    """The saturation cell of one size in one replicate: ``views`` by panel read at the cell's run length U_L, the cell's facts and slots."""

    views: Mapping[str, View]
    facts: int
    slots: int


def saturation_bits(side: SatSide, panel: str) -> float:
    """S(N) = F x i*(cell; U_L) bits."""
    return side.facts * side.views[panel].i_star(side.views[panel].run)[0]


def saturation_pair(small: SatSide, large: SatSide, *, ref_ok: bool, leakage: bool = False) -> StepResult:
    """Pair verdict in one replicate for the sizes N and 4N (section 8.10, first match wins): NOT_EVALUATED (REF fails for either row, or LEAKAGE), DEPENDENCE_FAILED (either cell fails DEP at a
    snapshot up to its run length), NOT FULL (either cell is not full on either panel: plateaued and i* at most 4.0), PROPORTIONAL (rho = S(4N)/S(N) at least 3.0 on both panels),
    SUBPROPORTIONAL (otherwise). Details: b(N) per panel, rho, the last doubling's gain and whether the cell is full."""
    d: dict[str, Any] = {}
    for tag, side in (("small", small), ("large", large)):
        d[tag] = {
            "slots": side.slots, "facts": side.facts,
            "b_bits_per_slot": {p: saturation_bits(side, p) / side.slots for p in core.PANELS},
            "last_doubling_gain": {p: side.views[p].i_star(side.views[p].run)[0] - side.views[p].i_star(side.views[p].run // 2)[0] for p in core.PANELS},
            "full": {p: side.views[p].loaded() for p in core.PANELS}, "plateau_status": {p: side.views[p].plateau_status() for p in core.PANELS},
        }  # fmt: skip
    if not ref_ok or leakage:
        return StepResult(NOT_EVALUATED, {**d, "reason": "REF failed" if not ref_ok else "LEAKAGE"})
    for side in (small, large):
        if any(v.dep(u) is False for v in side.views.values() for u in v.updates):
            return StepResult(DEPENDENCE_FAILED, d)
    if not all(d[t]["full"][p] for t in ("small", "large") for p in core.PANELS):
        return StepResult(NOT_FULL, d)
    rho = {p: saturation_bits(large, p) / saturation_bits(small, p) for p in core.PANELS}
    d["rho"] = rho
    if all(ge(r, core.SATURATION_RATIO) for r in rho.values()):
        return StepResult(PROPORTIONAL, d)
    return StepResult(SUBPROPORTIONAL, d)


def saturation_pair_class(verdicts: Sequence[str]) -> str:
    """Pair class over the five replicates (section 8.10, first match wins; the denominator is always 5): NOT_EVALUATED (at least 2), DEPENDENCE_FAILED (at least 2), NOT FULL (at least 2),
    PROPORTIONAL STEP (all 5), SUBPROPORTIONAL STEP (at least 4), MIXED."""
    if len(verdicts) != core.REPLICATES:
        raise ValueError("a pair class needs one verdict per replicate")
    c = Counter(verdicts)
    if c[NOT_EVALUATED] >= 2:
        return NOT_EVALUATED
    if c[DEPENDENCE_FAILED] >= 2:
        return DEPENDENCE_FAILED
    if c[NOT_FULL] >= 2:
        return NOT_FULL
    if c[PROPORTIONAL] == len(verdicts):
        return PROPORTIONAL_STEP
    if c[SUBPROPORTIONAL] >= core.PAIRED_MOST:
        return SUBPROPORTIONAL_STEP
    return MIXED


def saturation_arm_class(pair_classes: Sequence[str]) -> str:
    """Arm class over the pairs the arm reads (section 8.10, first match wins): SATURATION_NOT_MEASURED (every registered pair NOT FULL or NOT_EVALUATED), DEPENDENCE_FAILED (some registered pair),
    SATURATION_DOES_NOT_SCALE (some registered pair is a SUBPROPORTIONAL STEP), SATURATION_PROPORTIONAL_ALL_PAIRS (every registered pair is a PROPORTIONAL STEP), INTERMEDIATE otherwise. A pair fixed
    as '256 NOT MEASURED' (no 2K/256) is passed as NOT FULL, so it is never a PROPORTIONAL STEP (the lead's ruling 6: F-OQ is then INTERMEDIATE where 1,024 to 4,096 is proportional)."""
    if not pair_classes:
        raise ValueError("an arm reads at least one pair")
    if all(c in (NOT_FULL, NOT_EVALUATED) for c in pair_classes):
        return SAT_NOT_MEASURED
    if any(c == DEPENDENCE_FAILED for c in pair_classes):
        return DEPENDENCE_FAILED
    if any(c == SUBPROPORTIONAL_STEP for c in pair_classes):
        return SAT_DOES_NOT_SCALE
    if all(c == PROPORTIONAL_STEP for c in pair_classes):
        return SAT_PROPORTIONAL_ALL_PAIRS
    return INTERMEDIATE


def saturation_outcome(
    arm_classes: Mapping[str, str],
    *,
    engineering_failed: bool,
    incomplete: bool,
    pairs_read: Mapping[str, Sequence[str]] | None = None,
    sat256_absent: bool = False,
    details: Sequence[str] = (),
) -> "Outcome":
    """The saturation outcome (section 8.10; rows 1 and 2 of section 8.7 apply first). SATURATION-PROPORTIONAL: F-OQ, T-OQ or F-OQ-IVF is SATURATION_PROPORTIONAL_ALL_PAIRS. SATURATION-SUBPROPORTIONAL:
    F-OQ and T-OQ are both SATURATION_DOES_NOT_SCALE. SATURATION NOT MEASURED: F-OQ and T-OQ are both SATURATION_NOT_MEASURED. SATURATION-INCONCLUSIVE otherwise, with the reason (an arm class of
    DEPENDENCE_FAILED gives the reason DEPENDENCE_FAILED). H8 never gives SATURATION-PROPORTIONAL. Every printed outcome names '16,384 NOT MEASURED — NOT FUNDED'."""
    if engineering_failed:
        return Outcome(1, S1_ENGINEERING_FAILURE, ["an engineering gate failed or frozen and running identities differ"], S1_ENGINEERING_FAILURE + " (no scientific label on either line)")
    if incomplete:
        return Outcome(2, S1_INCOMPLETE, ["a registered cell lacks a record"], S1_INCOMPLETE + " (status; no outcome on either line)")
    pairs_read = pairs_read or {}
    notes = [NOT_FUNDED_16K, *([NOT_MEASURED_256] if sat256_absent else [])]
    proportional = [a for a in ("F-OQ", "T-OQ", "F-OQ-IVF") if arm_classes.get(a) == SAT_PROPORTIONAL_ALL_PAIRS]
    if proportional:
        named = [f"{a}: pairs {', '.join(pairs_read.get(a, ()))}" if pairs_read.get(a) else a for a in proportional]
        return Outcome(3, SAT_PROPORTIONAL, [], emit(tagged(SAT_PROPORTIONAL, *SAT_FIXED_PHRASES, *named, *notes, *details)))
    foq, toq = arm_classes.get("F-OQ"), arm_classes.get("T-OQ")
    if foq == SAT_DOES_NOT_SCALE and toq == SAT_DOES_NOT_SCALE:
        return Outcome(4, SAT_SUBPROPORTIONAL, ["F-OQ and T-OQ are both SATURATION_DOES_NOT_SCALE"], f"{SAT_SUBPROPORTIONAL} [{'; '.join([*SAT_FIXED_PHRASES, *notes, *details])}]")
    if foq == SAT_NOT_MEASURED and toq == SAT_NOT_MEASURED:
        return Outcome(5, SAT_NOT_MEASURED_OUTCOME, ["F-OQ and T-OQ are both SATURATION_NOT_MEASURED"], f"{SAT_NOT_MEASURED_OUTCOME} [{'; '.join(notes)}]")
    reasons = [f"{a}: {arm_classes.get(a, 'none')}" for a in ("F-OQ", "T-OQ")]
    if any(arm_classes.get(a) == DEPENDENCE_FAILED for a in ("F-OQ", "T-OQ", "F-OQ-IVF", "H8")):
        reasons.append("DEPENDENCE_FAILED")
    return Outcome(6, SAT_INCONCLUSIVE, reasons, tag_positives(f"{SAT_INCONCLUSIVE}: " + "; ".join(reasons) + f" [{'; '.join(notes)}]"))


def h8_annotations(undertrained_cells: Sequence[str]) -> dict[str, str]:
    """H8's annotations by grid cell (section 8.4): UNDERTRAINED-AT-U_P at a calibrated cell whose calibration a_use was below 0.90; H8 NOT CALIBRATED AT <cell> at 2K/1K, 8K/1K and 32K/4K, where
    H8 was not calibrated; nothing at a calibrated cell that reached 0.90."""
    calibrated = {core.cell_name(f, n) for f, n in core.H8_REPORT_CELLS}
    out: dict[str, str] = {}
    for f, n in core.GRID_CELLS:
        name = core.cell_name(f, n)
        if name not in calibrated:
            out[name] = f"{H8_NOT_CALIBRATED} {name}"
        elif name in undertrained_cells:
            out[name] = UNDERTRAINED
    return out


# --- capacity outcome (section 8.7) --------------------------------------------------------------------------------------------------------------
@dataclass
class ArmCapacity:
    arm: str
    cls: str
    dense: str  # the dense label (DENSE_AHEAD, BEATS_DENSE..., DENSE_MATCHES, DENSE_NOT_READ)
    capacity_steps: list[str] = field(default_factory=list)
    dense_text: str = ""
    dense_sat: str = ""  # the dense label at saturation (DENSE_HOLDS_MORE, STORE_HOLDS_MORE, SAME_AT_SATURATION); "" where it was not read
    dense_sat_sublabels: list[str] = field(default_factory=list)
    sat_class: str = ""  # the saturation arm class


class Outcome(NamedTuple):
    row: int
    label: str
    reasons: list[str]
    printed: str


def _is_ahead(a: ArmCapacity) -> bool:
    """DENSE AHEAD, or DENSE HOLDS MORE AT SATURATION, which counts as DENSE AHEAD for the arm in rows 3 and 4 of section 8.7 and in the milestone reading (section 8.5)."""
    return a.dense == DENSE_AHEAD or a.dense_sat == DENSE_HOLDS_MORE


def capacity_outcome(
    arms: Mapping[str, ArmCapacity],
    *,
    engineering_failed: bool,
    incomplete: bool,
    directed_transitions: Sequence[str] = (),
    every_step_not_loaded: bool = False,
    reasons_extra: Sequence[str] = (),
    printed_details: Sequence[str] = (),
) -> Outcome:
    """The capacity outcome (section 8.7, first match wins). CAPACITY-POSITIVE: F-OQ, T-OQ or F-OQ-IVF is CAPACITY_SUPPORTED and is not DENSE AHEAD (DENSE HOLDS MORE AT SATURATION counts as DENSE AHEAD);
    an arm whose CAPACITY STEP has no D-OQ read cannot by itself support CAPACITY_SUPPORTED (DENSE NOT READ). CAPACITY-NEGATIVE: (a) F-OQ and T-OQ are both CAPACITY_NOT_SUPPORTED; or (b) at least
    one of F-OQ, T-OQ, F-OQ-IVF is CAPACITY_SUPPORTED and every such arm is DENSE AHEAD (an empty set never satisfies (b)). NOT TESTED: for F-OQ and T-OQ every step is NOT LOADED, or the human lead
    directed it in the freeze record. Otherwise CAPACITY-INCONCLUSIVE with the reasons. Every outcome with a label prints '16,384→65,536 NOT TESTED'."""
    if engineering_failed:
        return Outcome(1, S1_ENGINEERING_FAILURE, ["an engineering gate failed or frozen and running identities differ"], S1_ENGINEERING_FAILURE + " (no scientific label on either line)")
    if incomplete:
        return Outcome(2, S1_INCOMPLETE, ["a registered cell lacks a record"], S1_INCOMPLETE + " (status; no outcome on either line)")
    learned = [arms[a] for a in core.LEARNED_KEY_ARMS if a in arms]
    supported = [a for a in learned if a.cls == CAPACITY_SUPPORTED]
    positive = [a for a in supported if a.dense not in (DENSE_AHEAD, DENSE_NOT_READ) and not _is_ahead(a)]
    if positive:
        names = ", ".join(a.arm for a in positive)
        details = [f"arm(s) {names}", *[f"{a.arm}: {a.dense}" + (f" ({a.dense_text})" if a.dense_text else "") + (f"; dense at saturation: {a.dense_sat}" if a.dense_sat else "") for a in positive], *printed_details]
        if any(dense_not_established(a.dense) for a in positive):
            details.append("DENSE COMPARISON NOT ESTABLISHED AT MATCHED COMPUTE")
        return Outcome(3, CAPACITY_POSITIVE, [], emit(tagged(CAPACITY_POSITIVE, "WITHIN REGISTERED RUN LENGTHS", SIZES_CAPACITY, NOT_TESTED_16K_65K, *details)))
    foq, toq = arms.get("F-OQ"), arms.get("T-OQ")
    if foq is not None and toq is not None and foq.cls == CAPACITY_NOT_SUPPORTED and toq.cls == CAPACITY_NOT_SUPPORTED:
        return Outcome(4, CAPACITY_NEGATIVE, ["(a) F-OQ and T-OQ are both CAPACITY_NOT_SUPPORTED"], f"{CAPACITY_NEGATIVE} (a) [{NOT_TESTED_16K_65K}]")
    if supported and all(_is_ahead(a) for a in supported):
        why = "; ".join(f"{a.arm}: {DENSE_AHEAD if a.dense == DENSE_AHEAD else DENSE_HOLDS_MORE}" for a in supported)
        return Outcome(4, CAPACITY_NEGATIVE, ["(b) every CAPACITY_SUPPORTED arm is DENSE AHEAD"], f"{CAPACITY_NEGATIVE} (b: DENSE AHEAD) [{why}; {NOT_TESTED_16K_65K}]")
    if directed_transitions or every_step_not_loaded:
        named = f" ({', '.join(directed_transitions)})" if directed_transitions else ""
        return Outcome(5, CAPACITY_NOT_TESTED, ["no loaded cell within budget" + named], f"{CAPACITY_NOT_TESTED}{named} [{NOT_TESTED_16K_65K}]")
    reasons = list(reasons_extra) or [f"{a.arm}: {a.cls}" for a in learned]
    if any(a.cls == CAPACITY_SUPPORTED and a.dense == DENSE_NOT_READ for a in learned):
        reasons.append("a CAPACITY_SUPPORTED arm has no D-OQ read at its CAPACITY STEP (DENSE NOT READ)")
    return Outcome(6, CAPACITY_INCONCLUSIVE, reasons, tag_positives(f"{CAPACITY_INCONCLUSIVE}: " + "; ".join(reasons) + f" [{NOT_TESTED_16K_65K}]"))


def milestone_reading(outcome: Outcome, arms: Mapping[str, ArmCapacity], work: Mapping[str, str], hierarchy: str, s0_status: str) -> str:
    """The reading for milestone question 1 on the capacity line with the saturation line and the dense labels (section 8.7), always printed with S0's status line. 'Storage half supported, as a
    necessary condition, from 1,024 to 16,384 slots' needs, for one SUBLINEAR arm (T-OQ, or F-OQ-IVF): CAPACITY-POSITIVE for that arm; not DENSE AHEAD, DENSE HOLDS MORE AT SATURATION included; its dense
    matched-compute reading established; its saturation class SATURATION_PROPORTIONAL_ALL_PAIRS; and the hierarchy label printed. If the arm is CAPACITY-POSITIVE and not DENSE AHEAD but its
    saturation class is not SATURATION_PROPORTIONAL_ALL_PAIRS: 'Capacity steps shown; proportional saturation not shown'."""
    suffix = f" | {s0_status} | {core.ORACLE_SENTENCE}"
    if outcome.label == CAPACITY_POSITIVE:
        sublinear = [a for a in ("T-OQ", "F-OQ-IVF") if a in arms and arms[a].cls == CAPACITY_SUPPORTED and arms[a].dense not in (DENSE_AHEAD, DENSE_NOT_READ) and not _is_ahead(arms[a]) and work.get(a) == SUBLINEAR]

        def established(a: str) -> bool:  # the capacity dense label and, read the conservative way, the sub-label at saturation
            return not dense_not_established(arms[a].dense) and DENSE_NOT_ESTABLISHED not in arms[a].dense_sat_sublabels

        sub = [a for a in sublinear if established(a)]
        if sublinear and not sub:
            return "Storage-half reading not available: the dense comparison is not established at matched compute (capacity shown under oracle addressing only)" + suffix
        full = [a for a in sub if arms[a].sat_class == SAT_PROPORTIONAL_ALL_PAIRS]
        if full:
            return emit(tagged("Storage half supported, as a necessary condition, from 1,024 to 16,384 slots", f"arm {full[0]}", f"hierarchy label {hierarchy}", f"saturation class {SAT_PROPORTIONAL_ALL_PAIRS}", NOT_TESTED_16K_65K, "says nothing about addressing by the model, use of the store by a language model, capability beyond recall of the trained facts, or any size above 16,384 slots")) + suffix
        if sub:
            return emit(tagged("Capacity steps shown; proportional saturation not shown", f"arm {sub[0]}", f"saturation class {arms[sub[0]].sat_class or 'not read'}", f"hierarchy label {hierarchy}", NOT_TESTED_16K_65K)) + suffix
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


def dense_faster(arm_ut: Sequence[Sequence[UT]], dense_ut: Sequence[Sequence[UT] | None], cost_arm: Mapping[str, float], cost_dense: Mapping[str, float]) -> str:
    """At the larger cell of a FASTER STEP (``arm_ut[replicate][panel]``, one u_T per panel): DENSE FASTER, a blocking label, if D-OQ's c_T is at most 0.8 of the arm's in both cost measures
    for every value the bounds allow, in at least 4 replicates, a replicate counting if EITHER panel satisfies it (section 22 (h)); DENSE SPEED UNDECIDED if it does not hold for every
    value but could hold for some value in at least 4 replicates (section 22 m3); DENSE NOT READ if there is no D-OQ cell; otherwise DENSE NOT FASTER."""
    if any(d is None for d in dense_ut):
        return DENSE_NOT_READ
    f = core.DENSE_FASTER_COST

    def sure(a: UT, d: UT) -> bool:
        return all(le(d.hi * cost_dense[m], f * a.lo * cost_arm[m]) for m in ("cpu", "madds"))

    def possible(a: UT, d: UT) -> bool:
        return all(le(d.lo * cost_dense[m], f * a.hi * cost_arm[m]) for m in ("cpu", "madds"))

    pairs = [list(zip(a, d, strict=True)) for a, d in zip(arm_ut, dense_ut, strict=True) if d is not None]
    if sum(1 for rep in pairs if any(sure(a, d) for a, d in rep)) >= core.PAIRED_MOST:
        return "DENSE FASTER"
    if sum(1 for rep in pairs if any(possible(a, d) for a, d in rep)) >= core.PAIRED_MOST:
        return DENSE_SPEED_UNDECIDED
    return "DENSE NOT FASTER"


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
        return Outcome(3, EFFICIENCY_POSITIVE, [], emit(tagged(EFFICIENCY_POSITIVE, SIZES_EFFICIENCY, f"arm(s) {', '.join(ok)}", *[f"{a}: {dense.get(a, DENSE_NOT_READ)}" for a in ok], *details)))
    if all(arm_classes.get(a) == "EFFICIENCY_NOT_SUPPORTED" for a in core.EFFICIENCY_ARMS):
        return Outcome(4, EFFICIENCY_NEGATIVE, ["F-OQ and T-OQ are both EFFICIENCY_NOT_SUPPORTED"], f"{EFFICIENCY_NEGATIVE} [{SIZES_EFFICIENCY}]")
    if supported and all(dense.get(a) == "DENSE FASTER" for a in supported):
        return Outcome(4, EFFICIENCY_NEGATIVE, ["every EFFICIENCY_SUPPORTED arm is DENSE FASTER"], f"{EFFICIENCY_NEGATIVE} (DENSE FASTER) [{SIZES_EFFICIENCY}]")
    reasons = [f"{a}: {arm_classes.get(a, 'none')}" for a in core.EFFICIENCY_ARMS]
    return Outcome(5, EFFICIENCY_INCONCLUSIVE, reasons, tag_positives(f"{EFFICIENCY_INCONCLUSIVE}: " + "; ".join(reasons) + f" [{SIZES_EFFICIENCY}]"))


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
