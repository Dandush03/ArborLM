# ruff: noqa: E501
"""P9 Lane A analysis (package I6): capacity classes, annotations and the ladder report.

Specification: ADR-0017 section 6.1 (I_acc), 8.1 (gates G1-G4, TASK_CEILING_FAIL), 8.2 (capacity: steps,
beats dense, dependence, plateau, the six classes with first-match precedence, the four annotations,
the ladder report), 10 (analysis dependencies: capacity classes need A1/A2 at all sizes including B102
and A8; annotations need A4 with A1 at 4K, A10, A7, A3).

Inputs are the ``core.EvalIndex`` of evaluation records keyed ``(label, update, stream)``: for a cell
the matched-exposure snapshot is ``core.updates(cell, E)`` (and ``U/2`` for the plateau rule), read on
``core.PANEL_STREAM['A']`` and ``['B']`` separately. The class of each panel is computed on its own and
disagreement gives NOT REPLICATED (order 1). Every function is a pure function of its inputs so that
synthetic inputs can trigger every class (required test). Thresholds are ``core`` constants; none is
chosen here. Nothing here raises on a missing record: a result whose records are missing is
``INCOMPLETE`` and lists them (the denominator is never reduced).

Readings the ADR leaves open are listed in ``READINGS`` (PENDING LEAD REVIEW); this module also holds
the helpers shared by ``analysis_b`` .. ``analysis_d`` and ``report``.

``controls`` (no record schema exists for it in ``core``; this is the layout read here)::

    {"g1": {"passed": bool}, "g4": {"passed": bool, "defects": [..]},
     "no_memory": {"panel_a": {"2048": {"correct": int, "facts": int}, "8192": .., "32768": ..,
                               "unseen": ..}, "panel_b": {..},
                   "lane_d_a_A": {"correct": int, "facts": int}, "lane_d_a_B": .., "lane_d_b_A": .., "lane_d_b_B": ..},
     "exact_accuracy": {"4096": 1.0, ..}, "probes": {"4096": {..}, ..}, "exact_lane_d": {..}}

Status: implementation self-checked only. Not independent review, not Astra validation, not human
approval.
"""

import math
from collections.abc import Collection, Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from typing import Any

from . import core
from .core import Cell, ClassResult, EvalIndex, EvalKey, EvalRecord

CAPACITY_CLASSES = (
    "NOT REPLICATED",
    "CAPACITY_NOT_SUPPORTED",
    "CAPACITY_POSITIVE",
    "CAPACITY_PARTIAL",
    "UNDERTRAINED",
    "INTERMEDIATE",
)
TREE_CLASSES = ("TREE_AHEAD", "TREE_COMPETITIVE", "TREE_BEHIND")
INCOMPLETE = "INCOMPLETE"
LADDER_REPORT = "LADDER_REPORT"
GATES_REPORT = "gates"
ESTIMANDS = ("matched", "fixed_compute")
STEPS: tuple[tuple[int, int], ...] = ((4096, 16384), (16384, 65536))
ARCH_BLOCK = {"flat": "A1", "learned_tree": "A2"}
A_EMPTY_SLOT = "EMPTY-SLOT-EFFECT"
A_OPT_DEP, A_OPT_UNINFORMATIVE = "OPTIMIZER-DEPENDENT", "OPTIMIZER-ARM UNINFORMATIVE"
A_OPT_NOT_ASSESSED = "OPTIMIZER-DEPENDENT: not assessed"
A_KEY_WIDTH, A_KEY_WIDTH_NOT_ASSESSED = "KEY-WIDTH-LIMITED", "KEY-WIDTH-LIMITED: not assessed"
A_EMPTY_NOT_ASSESSED = "EMPTY-SLOT-EFFECT: not assessed"
A_LEAKAGE = "LEAKAGE"
LADDER_TERMS = ("exact-R2", "R2-R1", "R1-R0a", "R0a-R0", "OB-treeR0")

# Readings of ADR text that is open to more than one reading (all PENDING LEAD REVIEW), reported to the lead.
READINGS: dict[str, str] = {
    "r01_seeds": "'both seeds' means the two B101 seeds (1701, 1702); the B102 replicate enters only where the ADR names it (step accuracy in every cell of the step; ratio >= 2.5)",
    "r02_dependence": "dependence needs value-permuted and disabled accuracy inside the G2 chance interval (not below it) and share_correct_with_support >= 0.90, in both B101 seeds; POSITIVE needs it at 16K and 64K, PARTIAL at 16K",
    "r03_beats_dense": "beats dense needs I > 0 as well as I >= 1.10 x dense I (an at-chance memory never beats a dense adapter at I = 0)",
    "r04_optimizer": "the optimizer annotation is blank when the row-lazy arm supports the step the AdamW arm supports; DEPENDENT and UNINFORMATIVE as written; A10 is flat-only so tree classes read 'OPTIMIZER-DEPENDENT: not assessed'",
    "r05_annotation_seeds": "annotations need their condition in both B101 seeds; a panel-specific annotation is printed with its panel",
    "r06_incomplete": "INCOMPLETE is per class, from the cells in ANALYSIS_DEPENDENCIES (ADR 10); a missing cell outside a class's dependencies blanks only the annotation that needs it ('not assessed')",
    "r07_tree_zero": "TREE_AHEAD needs tree I > 0; both trees at I = 0 read TREE_COMPETITIVE",
    "r08_ladder_material": "a ladder gap is material when it is >= 0.5 bits per fact (signed, positive) in both B101 seeds and both panels",
    "r09_fixed_compute": "classes are also computed at the fixed-compute snapshot (U_16K) and printed as a separate, secondary subject; the decision map reads the matched-exposure classes only",
    "r10_gates": "an explicit G1/G2/G4 failure makes the lane NOT_EVALUATED; a gate with no report is printed 'GATES NOT REPORTED' and does not block",
    "r11_leakage": "a LEAKAGE cell leaves the computed class visible but the lane is marked not interpreted (annotation LEAKAGE; the decision map ignores the class)",
    "r12_zero_ratio": "ratio with I_N = 0 is +inf; 0/0 gives 0 for I ratios (as the stub) and an undefined (nan) ratio elsewhere, which never satisfies a rule",
}


EVAL_REQUIRED = (
    "label",
    "update",
    "stream",
    "facts",
    "correct",
    "unseen_correct",
    "unseen_facts",
    "usage",
)


def valid_eval(rec: Mapping[str, Any]) -> bool:
    """True when ``rec`` carries every field the analyses read unconditionally (a malformed record is
    skipped by the loader and listed as unreadable, never allowed to crash an analysis)."""
    return (
        all(k in rec for k in EVAL_REQUIRED) and isinstance(rec["facts"], int) and rec["facts"] > 0
    )


class MissingRecord(KeyError):
    """A record needed by a rule is absent from the index (never escapes ``classify_*``)."""


# --- registry lookup -------------------------------------------------------------------------------------
_FIELDS = (
    "block",
    "arch",
    "slots",
    "rung",
    "key_width",
    "track",
    "optimizer",
    "alpha_u",
    "alpha_c",
    "parent",
    "seed",
    "lane_d_arm",
)
_registry_cache: tuple[int, dict[tuple[Any, ...], Cell]] | None = None


def _registry() -> dict[tuple[Any, ...], Cell]:
    """Lookup table over the ACTIVE registry (rebuilt when ``core`` installs or removes the DRY profile)."""
    global _registry_cache
    version = core.registry_version()
    if _registry_cache is None or _registry_cache[0] != version:
        table = {tuple(getattr(c, f) for f in _FIELDS): c for c in core.cells()}
        if len(table) != core.TOTAL_CELLS:  # pragma: no cover - guards the lookup key
            raise ValueError("P9 analysis lookup key is not unique over the registry")
        _registry_cache = (version, table)
    return _registry_cache[1]


def find_cell(
    block: str,
    arch: str,
    slots: int,
    *,
    rung: str = "R0",
    key_width: int = core.KEY_WIDTH,
    track: str = core.PROPORTIONAL,
    optimizer: str = core.ADAMW,
    alpha_u: float = 0.0,
    alpha_c: float = 0.0,
    parent: tuple[int, int] = core.PRIMARY_PARENT,
    seed: int = core.INIT_SEEDS[0],
    lane_d_arm: str | None = None,
) -> Cell | None:
    """The registered cell with these properties, or None when the registry has no such cell."""
    return _registry().get(
        (
            block,
            arch,
            slots,
            rung,
            key_width,
            track,
            optimizer,
            alpha_u,
            alpha_c,
            parent,
            seed,
            lane_d_arm,
        )
    )


def arm_cells(
    block: str,
    arch: str,
    slots: int,
    *,
    rung: str = "R0",
    key_width: int = core.KEY_WIDTH,
    optimizer: str = core.ADAMW,
    replicate: bool = True,
    track: str = core.PROPORTIONAL,
) -> list[Cell]:
    """The B101 cells of both seeds (1701, 1702) and, with ``replicate``, the B102 replicate cell."""
    out: list[Cell] = []
    for seed in core.INIT_SEEDS:
        cell = find_cell(
            block,
            arch,
            slots,
            rung=rung,
            key_width=key_width,
            optimizer=optimizer,
            track=track,
            seed=seed,
        )
        if cell is not None:
            out.append(cell)
    if replicate:
        cell = find_cell(
            block,
            arch,
            slots,
            rung=rung,
            key_width=key_width,
            optimizer=optimizer,
            track=track,
            parent=core.REPLICATE_PARENT,
            seed=core.INIT_SEEDS[0],
        )
        if cell is not None:
            out.append(cell)
    return out


def tag(cell: Cell) -> str:
    """``s1701`` for a B101 cell, ``b102_s1701`` for the replicate."""
    return (
        f"s{cell.seed}" if cell.parent == core.PRIMARY_PARENT else f"b{cell.parent[0]}_s{cell.seed}"
    )


# --- records ---------------------------------------------------------------------------------------------
def panel_stream(panel: str) -> str:
    if panel not in core.PANEL_STREAM:
        raise ValueError(f"unknown panel {panel!r}")
    return core.PANEL_STREAM[panel]


def snapshot_pair(cell: Cell, exposure: int, estimand: str = "matched") -> tuple[int, int]:
    """``(U/2, U)`` of the cell's own matched-exposure point, or of the fixed-compute point U_16K."""
    if estimand == "matched":
        u = core.updates(cell, exposure)
    elif estimand == "fixed_compute":
        u = core.fixed_compute_updates(exposure)
    else:
        raise ValueError(f"unknown estimand {estimand!r}")
    return u // 2, u


def get_record(index: EvalIndex, label: str, update: int, stream: str) -> EvalRecord:
    try:
        return index[(label, update, stream)]
    except KeyError:
        raise MissingRecord(f"{label}@{update}/{stream}") from None


def missing_keys(index: EvalIndex, needs: Iterable[EvalKey]) -> list[str]:
    return sorted(
        {
            f"{label}@{update}/{stream}"
            for (label, update, stream) in needs
            if (label, update, stream) not in index
        }
    )


def correct_of(rec: EvalRecord) -> int:
    return int(rec["correct"])


def accuracy_of(rec: EvalRecord) -> float:
    """correct / facts (ties already counted wrong by the evaluator)."""
    return rec["correct"] / rec["facts"]


@lru_cache(maxsize=1 << 16)
def _information(correct: int, facts: int, tests: int) -> float:
    return core.information_bits(correct, facts, tests)


@lru_cache(maxsize=256)
def _interval(facts: int, tests: int) -> core.ChanceInterval:
    return core.chance_interval(facts, tests)


def info_of(rec: EvalRecord, tests: int = core.G2_TESTS_PRIMARY) -> float:
    """I_acc in bits with the chance floor of ADR 6.1, from ``correct`` and ``facts`` (one source of truth,
    ``core.information_bits``; memoized because the interval costs O(facts))."""
    return _information(int(rec["correct"]), int(rec["facts"]), tests)


def bits_per_fact(rec: EvalRecord) -> float:
    return info_of(rec) / rec["facts"]


def is_chance(count: float, facts: int, tests: int = core.G2_TESTS_PRIMARY) -> bool:
    """Inside the exact G2 interval for ``facts`` facts (ADR 8.1: 'the same interval is chance')."""
    interval = _interval(facts, tests)
    return interval.low <= round(count) <= interval.high


def ratio(num: float, den: float) -> float:
    """num / den; den = 0 with num > 0 is +inf; 0/0 is nan (undefined: never satisfies a rule)."""
    if den > 0:
        return num / den
    return math.inf if num > 0 else math.nan


def information_ratio(i_small: float, i_large: float) -> float:
    """I_4N / I_N with I_N = 0 giving +inf (and 0/0 giving 0)."""
    if i_small > 0:
        return i_large / i_small
    return math.inf if i_large > 0 else 0.0


def plateaued(i_half: float, i_full: float) -> bool:
    """I(U) - I(U/2) <= 0.05 I(U) with I already floored by ``core.information_bits`` (a cell at chance
    at both snapshots has plateaued)."""
    return i_full - i_half <= core.PLATEAU_FRACTION * i_full


def ge(value: float, threshold: float) -> bool:
    """``value >= threshold``; nan is never at or above anything."""
    return value >= threshold


def combine_panels(
    panel_classes: Mapping[str, str], *, same: Mapping[str, str] | None = None
) -> str:
    """Order 1 of every table: the final class if the panels give one class, NOT REPLICATED if they differ.
    INCOMPLETE in any panel stays INCOMPLETE (a missing record is not a disagreement). ``same`` maps
    labels to a common name for the comparison (used where two labels mean 'no class')."""
    values = list(panel_classes.values())
    if INCOMPLETE in values:
        return INCOMPLETE
    norm = [(same or {}).get(v, v) for v in values]
    if len(set(norm)) == 1:
        return values[0] if len(set(values)) == 1 else norm[0]
    return core.NOT_REPLICATED


def merge_annotations(per_panel: Mapping[str, Sequence[str]]) -> list[str]:
    """Annotations present in every panel are printed as they are; those in only some panels carry the panel."""
    panels = list(per_panel)
    seen: list[str] = []
    for p in panels:
        for a in per_panel[p]:
            if a not in seen:
                seen.append(a)
    out: list[str] = []
    for a in seen:
        holders = [p for p in panels if a in per_panel[p]]
        out.append(a if len(holders) == len(panels) else f"{a} (panel {'/'.join(holders)} only)")
    return out


def make_result(
    lane: str,
    subject: str,
    cls: str,
    panel_classes: Mapping[str, str],
    annotations: Sequence[str],
    details: Mapping[str, Any],
) -> ClassResult:
    return ClassResult(
        lane=lane,
        subject=subject,
        cls=cls,
        panel_classes=dict(panel_classes),
        annotations=list(annotations),
        details=dict(details),
    )


def incomplete_result(lane: str, subject: str, missing: Sequence[str], **extra: Any) -> ClassResult:
    """No class: a record needed by the rule is missing (ADR 8.6; the denominator is not reduced)."""
    return make_result(
        lane,
        subject,
        INCOMPLETE,
        {p: INCOMPLETE for p in core.PANELS},
        [],
        {"missing": list(missing), **extra},
    )


def leaky_labels(index: EvalIndex) -> set[str]:
    """Labels of cells with a record whose unseen-fact accuracy is outside the G2 interval (LEAKAGE, ADR 8.1)."""
    out: set[str] = set()
    for (label, _update, _stream), rec in index.items():
        facts = int(rec.get("unseen_facts") or 0)
        if rec.get("leakage"):
            out.add(label)
        elif facts > 0 and not is_chance(int(rec["unseen_correct"]), facts):
            out.add(label)
    return out


def ceiling_fail_sizes(calibration: Mapping[str, Any] | None) -> tuple[int, ...]:
    """TASK_CEILING_FAIL sizes: ``calibration['task_ceiling_fail']`` if present, else derived from
    ``calibration['r2_accuracy']`` by ``core.select_exposure``."""
    if not calibration:
        return ()
    if "task_ceiling_fail" in calibration:
        return tuple(sorted(int(s) for s in calibration["task_ceiling_fail"]))
    curves = calibration.get("r2_accuracy")
    if isinstance(curves, Mapping):
        parsed = {int(s): {int(e): float(a) for e, a in c.items()} for s, c in curves.items()}
        return tuple(core.select_exposure(parsed)[1])
    return ()


def jsonable(value: Any) -> Any:
    """Plain JSON-safe copy: non-finite floats become the strings '+inf', '-inf' or None (nan)."""
    if isinstance(value, float):
        if math.isnan(value):
            return None
        if math.isinf(value):
            return "+inf" if value > 0 else "-inf"
        return value
    if isinstance(value, Mapping):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, list | tuple | set | frozenset):
        return [
            jsonable(v) for v in (sorted(value) if isinstance(value, set | frozenset) else value)
        ]
    return value


# --- steps -----------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class StepResult:
    """One size step N -> 4N for one panel: ``supported`` (accuracy >= 0.25 at both sizes in every cell
    of the step; I ratio >= 3.0 in both B101 seeds and >= 2.5 in the B102 replicate where one exists;
    a ratio with I_N = 0 is +inf), ``failing`` (in both seeds ratio < 2.0 or accuracy < 0.25 at the
    larger size), ``larger_plateaued``, and the ratios used."""

    slots_from: int
    slots_to: int
    supported: bool
    failing: bool
    larger_plateaued: bool
    ratios: dict[str, float]
    accuracies: dict[str, float]
    information: dict[str, float] = field(default_factory=dict)
    plateau: dict[str, bool] = field(default_factory=dict)


def _step(
    index: EvalIndex,
    small: Sequence[Cell],
    large: Sequence[Cell],
    panel: str,
    exposure: int,
    estimand: str,
) -> StepResult:
    stream = panel_stream(panel)
    pairs = {tag(c): c for c in small}
    ratios: dict[str, float] = {}
    accuracies: dict[str, float] = {}
    information: dict[str, float] = {}
    plateau: dict[str, bool] = {}
    supported = True
    failing_seeds: list[bool] = []
    plateau_seeds: list[bool] = []
    for cl in large:
        cs = pairs.get(tag(cl))
        if cs is None:
            raise MissingRecord(f"no smaller cell for {cl.label}")
        _, us = snapshot_pair(cs, exposure, estimand)
        half_l, full_l = snapshot_pair(cl, exposure, estimand)
        rs = get_record(index, cs.label, us, stream)
        rl = get_record(index, cl.label, full_l, stream)
        i_s, i_l = info_of(rs), info_of(rl)
        a_s, a_l = accuracy_of(rs), accuracy_of(rl)
        t = tag(cl)
        r = information_ratio(i_s, i_l)
        ratios[t] = r
        accuracies[f"{t}:small"], accuracies[f"{t}:large"] = a_s, a_l
        information[f"{t}:small"], information[f"{t}:large"] = i_s, i_l
        if a_s < core.STEP_ACCURACY_MIN or a_l < core.STEP_ACCURACY_MIN:
            supported = False
        threshold = (
            core.STEP_RATIO_B101 if cl.parent == core.PRIMARY_PARENT else core.STEP_RATIO_B102
        )
        if not ge(r, threshold):
            supported = False
        if cl.parent == core.PRIMARY_PARENT:
            failing_seeds.append(r < core.NOT_SUPPORTED_RATIO or a_l < core.STEP_ACCURACY_MIN)
            i_half = info_of(get_record(index, cl.label, half_l, stream))
            plateau[t] = plateaued(i_half, i_l)
            information[f"{t}:large_half"] = i_half
            plateau_seeds.append(plateau[t])
    if len(failing_seeds) != len(core.INIT_SEEDS):
        raise MissingRecord("a B101 seed cell of the step is not registered")
    return StepResult(
        slots_from=small[0].slots,
        slots_to=large[0].slots,
        supported=supported,
        failing=all(failing_seeds),
        larger_plateaued=all(plateau_seeds),
        ratios=ratios,
        accuracies=accuracies,
        information=information,
        plateau=plateau,
    )


def step_result(
    index: EvalIndex,
    arch: str,
    slots_from: int,
    panel: str,
    exposure: int,
    *,
    optimizer: str = "adamw",
    key_width: int = core.KEY_WIDTH,
    estimand: str = "matched",
) -> StepResult:
    """Evaluate one step for ``arch`` in {flat, learned_tree} (A1/A2) or the row-lazy arm (A10,
    ``optimizer='lazy'``; two B101 seeds only, no replicate) or key width 32 (A7, two B101 seeds only).
    Raises ``MissingRecord`` if a record is absent (``classify_*`` turns that into INCOMPLETE)."""
    slots_to = 4 * slots_from
    if optimizer == "lazy":
        block, replicate = "A10", False
    elif key_width != core.KEY_WIDTH:
        block, replicate = "A7", False
    else:
        block, replicate = ARCH_BLOCK[arch], True
    small = arm_cells(
        block, arch, slots_from, optimizer=optimizer, key_width=key_width, replicate=replicate
    )
    large = arm_cells(
        block, arch, slots_to, optimizer=optimizer, key_width=key_width, replicate=replicate
    )
    if not small or not large:
        raise MissingRecord(f"no registered cells for {block} {arch} {slots_from}->{slots_to}")
    return _step(index, small, large, panel, exposure, estimand)


def dense_cell(slots: int, seed: int) -> Cell | None:
    return find_cell("A8", "dense", slots, seed=seed)


def beats_dense(
    index: EvalIndex, arch: str, slots: int, panel: str, exposure: int, *, estimand: str = "matched"
) -> bool:
    """I >= 1.10 x the matched dense adapter's (A8), both seeds, at ``slots`` (and I > 0)."""
    stream = panel_stream(panel)
    for cell in arm_cells(ARCH_BLOCK[arch], arch, slots, replicate=False):
        dense = dense_cell(slots, cell.seed)
        if dense is None:
            raise MissingRecord(f"no dense cell at {slots} seed {cell.seed}")
        _, u = snapshot_pair(cell, exposure, estimand)
        _, ud = snapshot_pair(dense, exposure, estimand)
        i_mem = info_of(get_record(index, cell.label, u, stream))
        i_dense = info_of(get_record(index, dense.label, ud, stream))
        if not (i_mem > 0 and i_mem >= core.BEATS_DENSE_RATIO * i_dense):
            return False
    return True


def dependence_holds(
    index: EvalIndex, arch: str, slots: int, panel: str, exposure: int, *, estimand: str = "matched"
) -> bool:
    """Value permutation and disabling give chance accuracy (``core.chance_interval``) and at least 90%
    of correctly answered facts have a minimal support (both B101 seeds)."""
    stream = panel_stream(panel)
    for cell in arm_cells(ARCH_BLOCK[arch], arch, slots, replicate=False):
        _, u = snapshot_pair(cell, exposure, estimand)
        rec = get_record(index, cell.label, u, stream)
        facts = int(rec["facts"])
        permuted, disabled, share = (
            rec.get("value_permuted_accuracy"),
            rec.get("disabled_accuracy"),
            rec.get("share_correct_with_support"),
        )
        if permuted is None or disabled is None or share is None:
            return False
        if not (is_chance(permuted * facts, facts) and is_chance(disabled * facts, facts)):
            return False
        if share < core.DEPENDENCE_SUPPORT_SHARE:
            return False
    return True


@dataclass
class CapacityFacts:
    steps: dict[tuple[int, int], StepResult | None]
    beats: dict[int, bool]
    dependence: dict[int, bool]
    accuracy_64k: dict[str, float]
    used_labels: list[str]


def _capacity_facts(
    index: EvalIndex,
    arch: str,
    panel: str,
    exposure: int,
    estimand: str,
    ceiling_fail: Collection[int],
) -> CapacityFacts:
    stream = panel_stream(panel)
    steps: dict[tuple[int, int], StepResult | None] = {}
    for lo, hi in STEPS:
        steps[(lo, hi)] = (
            None
            if lo in ceiling_fail or hi in ceiling_fail
            else step_result(index, arch, lo, panel, exposure, estimand=estimand)
        )
    beats: dict[int, bool] = {}
    dependence: dict[int, bool] = {}
    for size in (16384, 65536):
        if size not in ceiling_fail:
            beats[size] = beats_dense(index, arch, size, panel, exposure, estimand=estimand)
            dependence[size] = dependence_holds(
                index, arch, size, panel, exposure, estimand=estimand
            )
    acc64: dict[str, float] = {}
    if 65536 not in ceiling_fail:
        for cell in arm_cells(ARCH_BLOCK[arch], arch, 65536, replicate=False):
            _, u = snapshot_pair(cell, exposure, estimand)
            acc64[tag(cell)] = accuracy_of(get_record(index, cell.label, u, stream))
    return CapacityFacts(steps, beats, dependence, acc64, [])


def _capacity_class(f: CapacityFacts) -> str:
    """Orders 2-6 of ADR 8.2, first matching rule wins; a step with a TASK_CEILING_FAIL size is not evaluated."""
    evaluated = [s for s in f.steps.values() if s is not None]
    if not evaluated:
        return core.NOT_EVALUATED
    if any(s.failing and s.larger_plateaued for s in evaluated):
        return "CAPACITY_NOT_SUPPORTED"
    s1, s2 = f.steps[STEPS[0]], f.steps[STEPS[1]]
    both = s1 is not None and s2 is not None and s1.supported and s2.supported
    if (
        both
        and f.beats.get(16384, False)
        and f.beats.get(65536, False)
        and f.dependence.get(16384, False)
        and f.dependence.get(65536, False)
        and len(f.accuracy_64k) == len(core.INIT_SEEDS)
        and all(a >= core.POSITIVE_ACCURACY_64K for a in f.accuracy_64k.values())
    ):
        return "CAPACITY_POSITIVE"
    if (
        s1 is not None
        and s1.supported
        and f.beats.get(16384, False)
        and f.dependence.get(16384, False)
    ):
        return "CAPACITY_PARTIAL"
    if any(not s.supported and not s.larger_plateaued for s in evaluated):
        return "UNDERTRAINED"
    return core.INTERMEDIATE


def classify_capacity_panel(
    index: EvalIndex,
    arch: str,
    panel: str,
    exposure: int,
    *,
    estimand: str = "matched",
    ceiling_fail: Collection[int] = (),
) -> str:
    """The first matching class of ADR 8.2 for one panel, orders 2-6 (order 1 is the panel rule).
    INCOMPLETE if a record is missing; NOT_EVALUATED if no step can be evaluated (TASK_CEILING_FAIL)."""
    try:
        return _capacity_class(
            _capacity_facts(index, arch, panel, exposure, estimand, ceiling_fail)
        )
    except MissingRecord:
        return INCOMPLETE


def capacity_needs(
    arch: str, exposure: int, estimand: str, ceiling_fail: Collection[int]
) -> list[EvalKey]:
    """Records the capacity class of ``arch`` needs (ADR 10): A1/A2 at every size that is not
    TASK_CEILING_FAIL including the B102 replicate (both snapshots), and A8 at those sizes."""
    needs: list[EvalKey] = []
    for size in core.SLOTS_BY_SIZE:
        if size in ceiling_fail:
            continue
        for cell in arm_cells(ARCH_BLOCK[arch], arch, size):
            half, full = snapshot_pair(cell, exposure, estimand)
            needs += [(cell.label, u, panel_stream(p)) for p in core.PANELS for u in (half, full)]
        for seed in core.INIT_SEEDS:
            dense = dense_cell(size, seed)
            if dense is not None:
                needs += [
                    (dense.label, snapshot_pair(dense, exposure, estimand)[1], panel_stream(p))
                    for p in core.PANELS
                ]
    return needs


# --- annotations -------------------------------------------------------------------------------------------
def empty_slot_effect(index: EvalIndex, panel: str, exposure: int) -> bool:
    """EMPTY-SLOT-EFFECT: at 2,048 fixed facts (A4 with A1 at 4K) I_acc per fact rises by more than 25%
    from 4K to 64K, read at the matched-exposure snapshot of the 2,048-fact set (open choice 6), in
    both B101 seeds."""
    stream = panel_stream(panel)
    for seed in core.INIT_SEEDS:
        base = find_cell("A1", "flat", 4096, seed=seed)
        wide = find_cell("A4", "flat", 65536, track=core.FIXED_TRACK, seed=seed)
        if base is None or wide is None:
            raise MissingRecord(f"no A1 4K or A4 64K cell for seed {seed}")
        p4 = bits_per_fact(get_record(index, base.label, core.updates(base, exposure), stream))
        p64 = bits_per_fact(get_record(index, wide.label, core.updates(wide, exposure), stream))
        if not p64 > (1.0 + core.EMPTY_SLOT_RISE) * p4:
            return False
    return True


def optimizer_annotation(
    index: EvalIndex,
    arch_step: tuple[int, int],
    panel: str,
    exposure: int,
    *,
    estimand: str = "matched",
) -> str:
    """OPTIMIZER-DEPENDENT if a step supported under AdamW is not supported in A10 and the row-lazy
    accuracy at the smaller size of the step is >= 0.25 in both seeds; OPTIMIZER-ARM UNINFORMATIVE if it
    is not supported there and that accuracy condition fails; '' when the step is not supported under
    AdamW or the row-lazy arm supports it too; 'OPTIMIZER-DEPENDENT: not assessed' when A10 records are
    absent. ``arch_step`` is ``(slots_from, slots_to)``; the AdamW arm is the flat A1."""
    lo, hi = arch_step
    if hi != 4 * lo:
        raise ValueError("a step is N -> 4N")
    try:
        adamw = step_result(index, "flat", lo, panel, exposure, estimand=estimand)
        if not adamw.supported:
            return ""
        lazy = step_result(index, "flat", lo, panel, exposure, optimizer="lazy", estimand=estimand)
    except MissingRecord:
        return A_OPT_NOT_ASSESSED
    if lazy.supported:
        return ""
    small_ok = all(
        lazy.accuracies[f"s{seed}:small"] >= core.STEP_ACCURACY_MIN for seed in core.INIT_SEEDS
    )
    return A_OPT_DEP if small_ok else A_OPT_UNINFORMATIVE


def key_width_limited(
    index: EvalIndex, panel: str, exposure: int, *, estimand: str = "matched"
) -> str:
    """KEY-WIDTH-LIMITED if key-32 R0 supports 16K -> 64K (two B101 seeds) and key-16 R0 does not;
    'KEY-WIDTH-LIMITED: not assessed' if A7 at 65,536 (or the key-16 cells) are absent."""
    try:
        wide = step_result(
            index, "flat", 16384, panel, exposure, key_width=core.KEY_WIDTH_WIDE, estimand=estimand
        )
        narrow = step_result(index, "flat", 16384, panel, exposure, estimand=estimand)
    except MissingRecord:
        return A_KEY_WIDTH_NOT_ASSESSED
    return A_KEY_WIDTH if wide.supported and not narrow.supported else ""


def _optimizer_for_class(
    index: EvalIndex, arch: str, panel: str, exposure: int, estimand: str
) -> list[str]:
    if arch != "flat":
        return [A_OPT_NOT_ASSESSED]
    found = [
        optimizer_annotation(index, step, panel, exposure, estimand=estimand) for step in STEPS
    ]
    if A_OPT_NOT_ASSESSED in found:
        return [A_OPT_NOT_ASSESSED]
    for wanted in (A_OPT_DEP, A_OPT_UNINFORMATIVE):
        if wanted in found:
            return [wanted]
    return []


def annotations_for_panel(
    index: EvalIndex, arch: str, panel: str, exposure: int, estimand: str
) -> list[str]:
    out: list[str] = []
    if arch == "flat":
        try:
            if empty_slot_effect(index, panel, exposure):
                out.append(A_EMPTY_SLOT)
        except MissingRecord:
            out.append(A_EMPTY_NOT_ASSESSED)
    out += _optimizer_for_class(index, arch, panel, exposure, estimand)
    if arch == "flat":
        kw = key_width_limited(index, panel, exposure, estimand=estimand)
        if kw:
            out.append(kw)
    return out


def classify_capacity(
    index: EvalIndex,
    arch: str,
    exposure: int,
    *,
    estimand: str = "matched",
    ceiling_fail: Collection[int] = (),
    leaky: Collection[str] = (),
) -> ClassResult:
    """Capacity class of ``arch`` (flat or learned_tree) with annotations: NOT REPLICATED if the panels
    disagree, else the class; TASK_CEILING_FAIL sizes make dependent steps NOT_EVALUATED (and
    CAPACITY_POSITIVE impossible if 65,536 fails; Lanes B-D NOT_EVALUATED if 16,384 fails)."""
    subject = f"capacity/{arch}" + ("" if estimand == "matched" else "/fixed_compute")
    fail = tuple(sorted(ceiling_fail))
    ceiling_notes = [f"TASK_CEILING_FAIL({s})" for s in fail]
    evaluable = [s for s in core.SLOTS_BY_SIZE if s not in fail]
    if not any(lo in evaluable and hi in evaluable for lo, hi in STEPS):
        return make_result(
            "A",
            subject,
            core.NOT_EVALUATED,
            {p: core.NOT_EVALUATED for p in core.PANELS},
            ceiling_notes,
            {"ceiling_fail": list(fail), "estimand": estimand, "exposure": exposure},
        )
    missing = missing_keys(index, capacity_needs(arch, exposure, estimand, fail))
    if missing:
        return incomplete_result(
            "A", subject, missing, estimand=estimand, exposure=exposure, ceiling_fail=list(fail)
        )
    panel_classes: dict[str, str] = {}
    per_panel_notes: dict[str, list[str]] = {}
    details: dict[str, Any] = {
        "estimand": estimand,
        "exposure": exposure,
        "ceiling_fail": list(fail),
        "panels": {},
    }
    for panel in core.PANELS:
        facts = _capacity_facts(index, arch, panel, exposure, estimand, fail)
        panel_classes[panel] = _capacity_class(facts)
        per_panel_notes[panel] = annotations_for_panel(index, arch, panel, exposure, estimand)
        details["panels"][panel] = {
            "steps": {
                f"{lo}->{hi}": (asdict(s) if s is not None else core.NOT_EVALUATED)
                for (lo, hi), s in facts.steps.items()
            },
            "beats_dense": {str(k): v for k, v in facts.beats.items()},
            "dependence": {str(k): v for k, v in facts.dependence.items()},
            "accuracy_64k": dict(facts.accuracy_64k),
        }
    cls = combine_panels(panel_classes)
    used = sorted(
        {c.label for size in evaluable for c in arm_cells(ARCH_BLOCK[arch], arch, size)}
        | {
            d.label
            for size in evaluable
            for seed in core.INIT_SEEDS
            if (d := dense_cell(size, seed)) is not None
        }
    )
    annotations = merge_annotations(per_panel_notes) + ceiling_notes
    if leaky and set(used) & set(leaky):
        annotations.append(A_LEAKAGE)
        details["interpretation_withheld"] = (
            "LEAKAGE: the lane is not interpreted until the auditor explains it"
        )
    details["used_labels"] = used
    return make_result("A", subject, cls, panel_classes, annotations, details)


# --- D03: tree against flat ----------------------------------------------------------------------------------
def tree_comparison(
    index: EvalIndex, exposure: int, *, estimand: str = "matched", leaky: Collection[str] = ()
) -> ClassResult:
    """D03: TREE_AHEAD if tree I_acc >= 1.03 x flat at 16K in both seeds and both panels,
    TREE_COMPETITIVE if >= 0.97, else TREE_BEHIND, with logical key products beside it and the fixed
    tree (A3) reported beside it. Logical work is analytical, never measured efficiency."""
    subject = "tree_comparison" + ("" if estimand == "matched" else "/fixed_compute")
    flat = arm_cells("A1", "flat", 16384, replicate=False)
    tree = arm_cells("A2", "learned_tree", 16384, replicate=False)
    fixed = arm_cells("A3", "fixed_tree", 16384, replicate=False)
    needs: list[EvalKey] = []
    for c in flat + tree + fixed:
        needs += [
            (c.label, snapshot_pair(c, exposure, estimand)[1], panel_stream(p)) for p in core.PANELS
        ]
    missing = missing_keys(index, needs)
    if missing:
        return incomplete_result("A", subject, missing, estimand=estimand)
    ratios: dict[str, float] = {}
    info: dict[str, dict[str, float]] = {}
    for panel in core.PANELS:
        for f, t in zip(flat, tree, strict=True):
            i_f = info_of(
                index[(f.label, snapshot_pair(f, exposure, estimand)[1], panel_stream(panel))]
            )
            i_t = info_of(
                index[(t.label, snapshot_pair(t, exposure, estimand)[1], panel_stream(panel))]
            )
            key = f"{panel}:{tag(f)}"
            ratios[key] = i_t / i_f if i_f > 0 else (math.inf if i_t > 0 else 1.0)
            info[key] = {"flat": i_f, "tree": i_t}
    lowest = min(ratios.values())
    tree_positive = all(v["tree"] > 0 for v in info.values())
    if lowest >= core.TREE_AHEAD_RATIO and tree_positive:
        cls = "TREE_AHEAD"
    elif lowest >= core.TREE_COMPETITIVE_RATIO:
        cls = "TREE_COMPETITIVE"
    else:
        cls = "TREE_BEHIND"
    fixed_info = {
        f"{panel}:{tag(c)}": info_of(
            index[(c.label, snapshot_pair(c, exposure, estimand)[1], panel_stream(panel))]
        )
        for panel in core.PANELS
        for c in fixed
    }
    details: dict[str, Any] = {
        "ratios_tree_over_flat": ratios,
        "lowest_ratio": lowest,
        "information_bits": info,
        "fixed_tree_information_bits": fixed_info,
        "logical_key_products": {
            "flat": core.logical_key_products("flat", 16384),
            "learned_tree": core.logical_key_products("learned_tree", 16384),
            "note": "analytical logical work per query (ADR 5.2); not a measured efficiency or speedup",
        },
        "estimand": estimand,
        "used_labels": sorted(c.label for c in flat + tree + fixed),
    }
    annotations: list[str] = []
    if leaky and set(details["used_labels"]) & set(leaky):
        annotations.append(A_LEAKAGE)
    return make_result("A", subject, cls, {p: cls for p in core.PANELS}, annotations, details)


# --- ladder -----------------------------------------------------------------------------------------------------
def _seed_bits(
    index: EvalIndex, cells: Sequence[Cell | None], panel: str, exposure: int, estimand: str
) -> dict[int, float | None]:
    out: dict[int, float | None] = {}
    for cell in cells:
        if cell is None:
            continue
        key = (cell.label, snapshot_pair(cell, exposure, estimand)[1], panel_stream(panel))
        out[cell.seed] = bits_per_fact(index[key]) if key in index else None
    return out


def _exact_bits(size: int, controls: Mapping[str, Any] | None) -> float:
    accuracy = (
        1.0  # G1 check 4: a dictionary lookup scores exactly 1.0 on trained facts (analytical)
    )
    if controls and "exact_accuracy" in controls:
        accuracy = float(controls["exact_accuracy"].get(str(size), accuracy))
    return core.fano_bits_per_fact(accuracy)


def ladder_report(
    index: EvalIndex,
    panel: str,
    exposure: int,
    *,
    estimand: str = "matched",
    controls: Mapping[str, Any] | None = None,
) -> dict[str, dict[str, float | None]]:
    """Per size, in Fano bits per fact with sign: exact - R2, R2 - R1, R1 - R0a, R0a - R0, and tree
    oracle branch - tree R0, with frozen-hidden probes beside R0; a gap is material at >= 0.5 bits. At
    4,096 slots only exact - R2 and R2 - R1 (R0a is not run). Never enters a class. Keys: the term
    (mean over the B101 seeds, None if either seed is missing), ``term|s1701`` and ``term|s1702``,
    and ``bits:<rung>`` for the rung values; undefined values are None."""
    report: dict[str, dict[str, float | None]] = {}
    for size in core.SLOTS_BY_SIZE:
        bits = {
            "R2": _seed_bits(
                index,
                [find_cell("A5", "flat", size, rung="R2", seed=s) for s in core.INIT_SEEDS],
                panel,
                exposure,
                estimand,
            ),
            "R1": _seed_bits(
                index,
                [find_cell("A5", "flat", size, rung="R1", seed=s) for s in core.INIT_SEEDS],
                panel,
                exposure,
                estimand,
            ),
            "R0a": _seed_bits(
                index,
                [find_cell("A5b", "flat", size, rung="R0a", seed=s) for s in core.INIT_SEEDS],
                panel,
                exposure,
                estimand,
            ),
            "R0": _seed_bits(
                index,
                [find_cell("A1", "flat", size, seed=s) for s in core.INIT_SEEDS],
                panel,
                exposure,
                estimand,
            ),
            "treeR0": _seed_bits(
                index,
                [find_cell("A2", "learned_tree", size, seed=s) for s in core.INIT_SEEDS],
                panel,
                exposure,
                estimand,
            ),
            "OB": _seed_bits(
                index,
                [find_cell("A6", "learned_tree", size, rung="OB", seed=s) for s in core.INIT_SEEDS],
                panel,
                exposure,
                estimand,
            ),
            "treeR1": _seed_bits(
                index,
                [find_cell("A6", "learned_tree", size, rung="R1", seed=s) for s in core.INIT_SEEDS],
                panel,
                exposure,
                estimand,
            ),
        }
        exact = _exact_bits(size, controls)
        row: dict[str, float | None] = {}

        def put(term: str, per_seed: dict[int, float | None]) -> None:
            for seed in core.INIT_SEEDS:
                row[f"{term}|s{seed}"] = per_seed.get(seed)
            have = [per_seed.get(seed) for seed in core.INIT_SEEDS]
            row[term] = (
                sum(v for v in have if v is not None) / len(have)
                if all(v is not None for v in have)
                else None
            )

        def gap(
            hi: Mapping[int, float | None] | float, lo: Mapping[int, float | None]
        ) -> dict[int, float | None]:
            out: dict[int, float | None] = {}
            for seed in core.INIT_SEEDS:
                h = hi if isinstance(hi, float) else hi.get(seed)
                low = lo.get(seed)
                out[seed] = None if h is None or low is None else h - low
            return out

        put("exact-R2", gap(exact, bits["R2"]))
        put("R2-R1", gap(bits["R2"], bits["R1"]))
        if size != core.SLOTS_BY_SIZE[0]:
            put("R1-R0a", gap(bits["R1"], bits["R0a"]))
            put("R0a-R0", gap(bits["R0a"], bits["R0"]))
        if size == 16384:
            put("OB-treeR0", gap(bits["OB"], bits["treeR0"]))
        for rung, per_seed in bits.items():
            vals = [per_seed.get(seed) for seed in core.INIT_SEEDS]
            row[f"bits:{rung}"] = (
                sum(v for v in vals if v is not None) / len(vals)
                if all(v is not None for v in vals)
                else None
            )
        row["bits:exact"] = exact
        report[str(size)] = row
    return report


def material_terms(
    panel_reports: Mapping[str, Mapping[str, Mapping[str, float | None]]],
) -> list[str]:
    """Terms ``'<size>:<term>'`` whose gap is >= 0.5 bits per fact in both B101 seeds and both panels."""
    out: list[str] = []
    if not panel_reports:
        return out
    first = next(iter(panel_reports.values()))
    for size, row in first.items():
        for term in LADDER_TERMS:
            if term not in row:
                continue
            values = [
                r[size].get(f"{term}|s{seed}")
                for r in panel_reports.values()
                for seed in core.INIT_SEEDS
            ]
            if all(v is not None and v >= core.LADDER_MATERIAL_BITS for v in values):
                out.append(f"{size}:{term}")
    return out


# --- gates ---------------------------------------------------------------------------------------------------------
def _gate_status(report: Mapping[str, Any] | None) -> str:
    if report is None:
        return "not_reported"
    return "pass" if report.get("passed") else "fail"


def task_gates(
    index: EvalIndex,
    calibration: Mapping[str, Any] | None,
    controls: Mapping[str, Any] | None = None,
) -> dict[str, str]:
    """G1-G4 outcomes ('pass', 'fail' or 'not_reported') and TASK_CEILING_FAIL sizes from the calibration
    and generator reports (``controls['g1']``, ``['g4']``, ``['no_memory']``); G2 tests every reported
    no-memory baseline against the exact interval of its fact count; G3 is decided in the calibration."""
    controls = controls or {}
    g2 = "not_reported"
    no_memory = controls.get("no_memory")
    if isinstance(no_memory, Mapping) and no_memory:
        failures: list[str] = []
        for stream, entry in no_memory.items():
            counts = (
                entry
                if "correct" in entry
                else {k: v for k, v in entry.items() if isinstance(v, Mapping)}
            )
            items = (
                [(stream, entry)]
                if "correct" in entry
                else [(f"{stream}/{k}", v) for k, v in counts.items()]
            )
            for name, value in items:
                tests = (
                    core.G2_TESTS_LANE_D
                    if str(stream).startswith("lane_d")
                    else core.G2_TESTS_PRIMARY
                )
                if not is_chance(int(value["correct"]), int(value["facts"]), tests):
                    failures.append(name)
        g2 = "fail" if failures else "pass"
    fail = ceiling_fail_sizes(calibration)
    return {
        "G1": _gate_status(controls.get("g1")),
        "G2": g2,
        "G3": ("TASK_CEILING_FAIL: " + ",".join(map(str, fail)))
        if fail
        else ("pass" if calibration else "not_reported"),
        "G4": _gate_status(controls.get("g4")),
        "TASK_CEILING_FAIL": ",".join(map(str, fail)) if fail else "none",
    }


def gates_blocking(gates: Mapping[str, str]) -> list[str]:
    """Gates that explicitly failed (G1, G2, G4); G3 is handled by the TASK_CEILING_FAIL consequences."""
    return [g for g in ("G1", "G2", "G4") if gates.get(g) == "fail"]


def gates_result(
    index: EvalIndex,
    calibration: Mapping[str, Any] | None,
    controls: Mapping[str, Any] | None = None,
) -> ClassResult:
    gates = task_gates(index, calibration, controls)
    notes = [f"GATE_FAILED({g})" for g in gates_blocking(gates)]
    if any(v == "not_reported" for k, v in gates.items() if k in ("G1", "G2", "G4")):
        notes.append("GATES NOT REPORTED")
    cls = (
        "GATES_FAILED"
        if gates_blocking(gates)
        else ("TASK_CEILING_FAIL" if gates["TASK_CEILING_FAIL"] != "none" else "GATES_PASSED")
    )
    details = {
        **gates,
        "ceiling_fail": list(ceiling_fail_sizes(calibration)),
        "leakage": sorted(leaky_labels(index)),
    }
    return make_result("A", GATES_REPORT, cls, {p: cls for p in core.PANELS}, notes, details)


def analyze(
    index: EvalIndex,
    exposure: int,
    calibration: Mapping[str, Any] | None,
    controls: Mapping[str, Any] | None = None,
) -> list[ClassResult]:
    """All Lane A results: flat and learned-tree capacity classes with annotations (matched exposure,
    and a secondary fixed-compute subject), tree comparison, ladder report (as a ClassResult with class
    'LADDER_REPORT') and gates. Never raises on missing records."""
    calibration = calibration or {}
    fail = ceiling_fail_sizes(calibration)
    leaky = leaky_labels(index)
    gates = task_gates(index, calibration, controls)
    blocked = gates_blocking(gates)
    results: list[ClassResult] = []
    for estimand in ESTIMANDS:
        for arch in ARCH_BLOCK:
            res = classify_capacity(
                index, arch, exposure, estimand=estimand, ceiling_fail=fail, leaky=leaky
            )
            if blocked and res["cls"] not in (core.NOT_EVALUATED, INCOMPLETE):
                res["details"]["class_if_gates_passed"] = res["cls"]
                res["annotations"] += [f"GATE_FAILED({g})" for g in blocked]
                res["cls"] = core.NOT_EVALUATED
            results.append(res)
    for estimand in ESTIMANDS:
        tree = (
            tree_comparison(index, exposure, estimand=estimand, leaky=leaky)
            if 16384 not in fail
            else make_result(
                "A",
                "tree_comparison" + ("" if estimand == "matched" else "/fixed_compute"),
                core.NOT_EVALUATED,
                {p: core.NOT_EVALUATED for p in core.PANELS},
                ["TASK_CEILING_FAIL(16384)"],
                {},
            )
        )
        results.append(tree)
    ladders = {p: ladder_report(index, p, exposure, controls=controls) for p in core.PANELS}
    material = material_terms(ladders)
    probes = (controls or {}).get("probes")
    results.append(
        make_result(
            "A",
            "ladder",
            LADDER_REPORT,
            {p: LADDER_REPORT for p in core.PANELS},
            [],
            {
                "panels": ladders,
                "material": material,
                "probes": probes,
                "note": "R0a, R1, R2 and oracle-branch results are not system results; the ladder gives no upper bounds (ADR 5.3, 13)",
            },
        )
    )
    results.append(gates_result(index, calibration, controls))
    return results
