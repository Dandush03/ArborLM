# ruff: noqa: E501
"""P9 Lane B analysis (package I6): utilization classes and the optimization annotations.

Specification: ADR-0017 section 6.3 (REGULARIZER-DRIVEN MOVEMENT), 7 (SOFT-USAGE ONLY), 8.3 (the
utilization classes; first match wins).

Reference of a case: the dose-zero 16K cell of the same architecture and seed for B1 cells; the B1 cell
with alpha_u = 0.25, alpha_c = 0 of the same architecture and seed for C1 cells (``reference_label``).
Every rule is evaluated per seed against the reference of the same seed and must hold in both seeds
and both panels: the class of a seed is the first matching row; the seeds give one class if they agree
and INTERMEDIATE if they disagree; panels that disagree give NOT REPLICATED. Lane B classes need
dose-zero 16K accuracy >= 0.25 in both seeds (and both panels), else NOT_EVALUATED. If U* is NOT
INTERPRETABLE for the case or its reference, COLLAPSED is decided by the I ratio alone and
ENTROPY_INFLATION, IMPROVED and PRESERVED become INTERMEDIATE. Entropy-effective slots here come from
hard top-8 selections at answer sites.

``EvalRecord.usage`` keys read here (``USAGE_KEYS``; the record schema in ``core`` leaves the dict open):
``entropy_effective_hard`` (slots, exp of the hard answer-site entropy), ``entropy_soft`` (H(u) from the
soft inclusion, nats), ``key_movement_without_task_grad`` (cumulative key movement on updates where the
row had no task gradient, summed over rows), ``key_movement_share_without``.

Status: implementation self-checked only. Not independent review, not Astra validation, not human
approval.
"""

import math
from collections.abc import Collection
from dataclasses import dataclass
from typing import Any

from . import core
from .analysis_a import (
    INCOMPLETE,
    MissingRecord,
    accuracy_of,
    combine_panels,
    find_cell,
    get_record,
    incomplete_result,
    info_of,
    information_ratio,
    leaky_labels,
    make_result,
    merge_annotations,
    missing_keys,
    panel_stream,
    ratio,
    snapshot_pair,
)
from .core import Cell, ClassResult, EvalIndex, EvalKey, EvalRecord

UTILIZATION_CLASSES = (
    "NOT REPLICATED",
    "COLLAPSED",
    "ENTROPY_INFLATION",
    "UTILIZATION_IMPROVED",
    "UTILIZATION_PRESERVED",
    "NO DIFFERENCE / INTERMEDIATE",
)
NO_DIFFERENCE = "NO DIFFERENCE / INTERMEDIATE"
INDETERMINATE = {NO_DIFFERENCE: core.INTERMEDIATE}
SOFT_USAGE_ONLY = "SOFT-USAGE ONLY"
REGULARIZER_MOVEMENT = "REGULARIZER-DRIVEN MOVEMENT"
LEAKAGE = "LEAKAGE"
USAGE_KEYS = {
    "hard_effective": "entropy_effective_hard",
    "soft_entropy": "entropy_soft",
    "movement_without": "key_movement_without_task_grad",
    "movement_share_without": "key_movement_share_without",
}
ARCH_BLOCK = {"flat": "A1", "learned_tree": "A2"}


def reference_cell(cell: Cell) -> Cell | None:
    """The reference cell of a B1 or C1 cell (same architecture, parent and seed)."""
    if cell.block == "B1":
        return find_cell(
            ARCH_BLOCK[cell.arch], cell.arch, cell.slots, parent=cell.parent, seed=cell.seed
        )
    if cell.block == "C1":
        return find_cell(
            "B1",
            cell.arch,
            cell.slots,
            alpha_u=core.ALPHA_C_WITH_ALPHA_U,
            alpha_c=0.0,
            parent=cell.parent,
            seed=cell.seed,
        )
    raise ValueError(f"{cell.label} is not a B1 or C1 cell")


def reference_label(cell: Cell) -> str:
    """Label of the reference cell of a B1 or C1 cell (same architecture, parent and seed)."""
    ref = reference_cell(cell)
    if ref is None:  # pragma: no cover - the registry always has it
        raise ValueError(f"no reference cell for {cell.label}")
    return ref.label


def usage_value(rec: EvalRecord, key: str) -> float | None:
    value = rec.get("usage", {}).get(USAGE_KEYS.get(key, key))
    return None if value is None else float(value)


def lane_b_evaluable(
    index: EvalIndex, exposure: int, *, estimand: str = "matched"
) -> dict[str, bool]:
    """Per architecture: dose-zero 16K accuracy >= 0.25 in both seeds and both panels (else Lane B is
    NOT_EVALUATED). A missing record counts as not evaluable (the class result then says INCOMPLETE)."""
    out: dict[str, bool] = {}
    for arch, block in ARCH_BLOCK.items():
        ok = True
        for seed in core.INIT_SEEDS:
            cell = find_cell(block, arch, 16384, seed=seed)
            for panel in core.PANELS:
                key = (
                    (cell.label, snapshot_pair(cell, exposure, estimand)[1], panel_stream(panel))
                    if cell
                    else None
                )
                if (
                    key is None
                    or key not in index
                    or accuracy_of(index[key]) < core.LANE_B_MIN_ACCURACY
                ):
                    ok = False
        out[arch] = ok
    return out


@dataclass(frozen=True)
class SeedNumbers:
    """Ratios of one case cell against its reference of the same seed, on one panel (nan = undefined)."""

    i_ratio: float
    ustar_ratio: float
    eff_ratio: float
    support_ratio: float
    accuracy_drop: float
    ustar_interpretable: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "I": self.i_ratio,
            "ustar": self.ustar_ratio,
            "eff_hard": self.eff_ratio,
            "support_length": self.support_ratio,
            "accuracy_drop": self.accuracy_drop,
            "ustar_interpretable": self.ustar_interpretable,
        }


def _eval_key(cell: Cell, exposure: int, panel: str, estimand: str) -> EvalKey:
    return (cell.label, snapshot_pair(cell, exposure, estimand)[1], panel_stream(panel))


def seed_numbers(
    index: EvalIndex,
    case: Cell,
    panel: str,
    exposure: int,
    *,
    estimand: str = "matched",
    reference: Cell | None = None,
) -> SeedNumbers:
    """The ratios of ``case`` to its reference (default: ``reference_cell``). Raises ``MissingRecord``."""
    ref = reference or reference_cell(case)
    if ref is None:
        raise MissingRecord(f"no reference for {case.label}")
    rc = get_record(index, *_eval_key(case, exposure, panel, estimand))
    rr = get_record(index, *_eval_key(ref, exposure, panel, estimand))

    def num(rec: EvalRecord, name: str) -> float:
        value: Any = dict(rec).get(name)
        return math.nan if value is None else float(value)

    eff_c, eff_r = usage_value(rc, "hard_effective"), usage_value(rr, "hard_effective")
    return SeedNumbers(
        i_ratio=information_ratio(info_of(rr), info_of(rc)),
        ustar_ratio=ratio(num(rc, "useful_slots"), num(rr, "useful_slots")),
        eff_ratio=ratio(eff_c, eff_r) if eff_c is not None and eff_r is not None else math.nan,
        support_ratio=ratio(num(rc, "mean_support_length"), num(rr, "mean_support_length")),
        accuracy_drop=accuracy_of(rr) - accuracy_of(rc),
        ustar_interpretable=rc.get("ustar_interpretable") is True
        and rr.get("ustar_interpretable") is True,
    )


def utilization_ratios(
    index: EvalIndex,
    case: Cell,
    panel: str,
    exposure: int,
    *,
    estimand: str = "matched",
    reference: Cell | None = None,
) -> dict[str, float]:
    """Ratios of one case cell (its own seed) against the reference of the same seed: I, U*,
    entropy-effective slots (hard), mean minimal support length, and the accuracy drop; keyed
    ``<name>_s1701`` / ``<name>_s1702`` by the case's seed; nan is undefined."""
    n = seed_numbers(index, case, panel, exposure, estimand=estimand, reference=reference)
    return {f"{k}_s{case.seed}": v for k, v in n.as_dict().items() if k != "ustar_interpretable"}


def class_from_numbers(n: SeedNumbers) -> str:
    """Rows 2-6 of ADR 8.3 for one seed and one panel (first match wins). nan never satisfies a rule."""
    if n.i_ratio < core.UTIL_I_COLLAPSED or (
        n.ustar_interpretable and n.ustar_ratio < core.UTIL_USTAR_COLLAPSED
    ):
        return "COLLAPSED"
    if not n.ustar_interpretable:
        return core.INTERMEDIATE  # ENTROPY_INFLATION, IMPROVED and PRESERVED need U* (ADR 8.3)
    if (
        n.eff_ratio >= core.UTIL_EFF_INFLATION
        and n.i_ratio < core.UTIL_NO_GAIN
        and n.ustar_ratio < core.UTIL_NO_GAIN
    ):
        return "ENTROPY_INFLATION"
    if (
        n.i_ratio >= core.UTIL_IMPROVED
        and n.ustar_ratio >= core.UTIL_IMPROVED
        and n.support_ratio <= core.UTIL_SUPPORT_LENGTH_MAX
    ):
        return "UTILIZATION_IMPROVED"
    if (
        n.i_ratio >= core.UTIL_PRESERVED
        and n.accuracy_drop <= core.UTIL_ACCURACY_DROP_MAX
        and n.ustar_ratio >= core.UTIL_PRESERVED
    ):
        return "UTILIZATION_PRESERVED"
    return NO_DIFFERENCE


def classify_utilization_panel(
    index: EvalIndex,
    case: Cell,
    panel: str,
    exposure: int,
    *,
    estimand: str = "matched",
    reference: Cell | None = None,
) -> str:
    """Rules 2-6 of ADR 8.3 for one panel and one seed's cell: COLLAPSED (U* ratio < 0.80 or I ratio <
    0.90), ENTROPY_INFLATION (eff ratio >= 1.25, I ratio < 1.03, U* ratio < 1.03), UTILIZATION_IMPROVED
    (I and U* ratios >= 1.05 and support-length ratio <= 1.10), UTILIZATION_PRESERVED (I ratio >= 0.97,
    drop <= 0.02, U* ratio >= 0.97), else NO DIFFERENCE / INTERMEDIATE. INCOMPLETE if a record is
    missing."""
    try:
        return class_from_numbers(
            seed_numbers(index, case, panel, exposure, estimand=estimand, reference=reference)
        )
    except MissingRecord:
        return INCOMPLETE


def combine_seeds(seed_classes: list[str]) -> str:
    """One class if every seed gives it, INTERMEDIATE if the seeds disagree (ADR 8.3)."""
    if INCOMPLETE in seed_classes:
        return INCOMPLETE
    return seed_classes[0] if len(set(seed_classes)) == 1 else core.INTERMEDIATE


def soft_usage_only(
    index: EvalIndex, case: Cell, panel: str, exposure: int, *, estimand: str = "matched"
) -> bool:
    """SOFT-USAGE ONLY: soft H(u) >= ln M while the hard entropy-effective-slot ratio to the reference
    is below 1.05 (ADR 7). False when a needed usage value is not recorded."""
    n = seed_numbers(index, case, panel, exposure, estimand=estimand)
    rc = get_record(index, *_eval_key(case, exposure, panel, estimand))
    soft = usage_value(rc, "soft_entropy")
    if soft is None or math.isnan(n.eff_ratio):
        return False
    floor = math.log(core.usage_floor_support(case.slots, case.facts))
    return soft >= floor and n.eff_ratio < core.SOFT_USAGE_ONLY_RATIO


def _movement(index: EvalIndex, cell: Cell, exposure: int, estimand: str) -> float | None:
    for panel in core.PANELS:
        key = _eval_key(cell, exposure, panel, estimand)
        if key in index:
            return usage_value(index[key], "movement_without")
    raise MissingRecord(cell.label)


def regularizer_driven_movement(
    index: EvalIndex, case: Cell, exposure: int, *, estimand: str = "matched"
) -> bool:
    """REGULARIZER-DRIVEN MOVEMENT for this seed: the cell's cumulative key movement on updates where the
    row had no task gradient exceeds 1.5 x that of its reference (``core.REGULARIZER_MOVEMENT_RATIO``).
    The class annotation needs it in both seeds."""
    ref = reference_cell(case)
    if ref is None:
        raise MissingRecord(case.label)
    mine, theirs = (
        _movement(index, case, exposure, estimand),
        _movement(index, ref, exposure, estimand),
    )
    if mine is None or theirs is None:
        return False
    return mine > core.REGULARIZER_MOVEMENT_RATIO * theirs


def case_needs(
    case_group: list[Cell], exposure: int, estimand: str, *, with_reference: bool = True
) -> list[EvalKey]:
    needs: list[EvalKey] = []
    for case in case_group:
        cells = [case]
        if with_reference:
            ref = reference_cell(case)
            if ref is not None:
                cells.append(ref)
        for cell in cells:
            needs += [_eval_key(cell, exposure, p, estimand) for p in core.PANELS]
    return needs


def subject_of(case: Cell) -> str:
    return f"{case.block}/{case.arch}/au{case.alpha_u:g}/ac{case.alpha_c:g}"


def classify_utilization(
    index: EvalIndex,
    case_group: list[Cell],
    exposure: int,
    *,
    estimand: str = "matched",
    ceiling_fail: Collection[int] = (),
    leaky: Collection[str] | None = None,
) -> ClassResult:
    """Class of one case (both seeds of one architecture and dose) with annotations SOFT-USAGE ONLY and
    REGULARIZER-DRIVEN MOVEMENT; ``case_group`` holds the two seed cells. B1 groups need the dose-zero
    16K accuracy >= 0.25 in both seeds (else NOT_EVALUATED); 16,384 being TASK_CEILING_FAIL makes the
    result NOT_EVALUATED. Missing records give INCOMPLETE."""
    first = case_group[0]
    subject, lane = subject_of(first), first.lane
    if sorted(c.seed for c in case_group) != sorted(core.INIT_SEEDS):
        raise ValueError("a case group holds one cell per initialization seed")
    if first.slots in set(ceiling_fail):
        return make_result(
            lane,
            subject,
            core.NOT_EVALUATED,
            {p: core.NOT_EVALUATED for p in core.PANELS},
            [f"TASK_CEILING_FAIL({first.slots})"],
            {"estimand": estimand},
        )
    missing = missing_keys(index, case_needs(case_group, exposure, estimand))
    if missing:
        return incomplete_result(lane, subject, missing, estimand=estimand)
    if first.block == "B1" and not lane_b_evaluable(index, exposure, estimand=estimand)[first.arch]:
        return make_result(
            lane,
            subject,
            core.NOT_EVALUATED,
            {p: core.NOT_EVALUATED for p in core.PANELS},
            [],
            {
                "reason": "dose-zero 16K accuracy below 0.25 in a seed or panel",
                "estimand": estimand,
            },
        )
    panel_classes: dict[str, str] = {}
    notes: dict[str, list[str]] = {}
    details: dict[str, Any] = {
        "estimand": estimand,
        "exposure": exposure,
        "panels": {},
        "reference_labels": {str(c.seed): reference_label(c) for c in case_group},
    }
    for panel in core.PANELS:
        seeds: dict[str, str] = {}
        nums: dict[str, Any] = {}
        soft: list[bool] = []
        movement: list[bool] = []
        for case in sorted(case_group, key=lambda c: c.seed):
            n = seed_numbers(index, case, panel, exposure, estimand=estimand)
            seeds[str(case.seed)] = class_from_numbers(n)
            nums[str(case.seed)] = n.as_dict()
            soft.append(soft_usage_only(index, case, panel, exposure, estimand=estimand))
            movement.append(regularizer_driven_movement(index, case, exposure, estimand=estimand))
            rec = index[_eval_key(case, exposure, panel, estimand)]
            nums[str(case.seed)]["per_fact_file"] = rec.get("per_fact_file")
        panel_classes[panel] = combine_seeds(list(seeds.values()))
        notes[panel] = ([SOFT_USAGE_ONLY] if all(soft) else []) + (
            [REGULARIZER_MOVEMENT] if all(movement) else []
        )
        details["panels"][panel] = {"seed_classes": seeds, "numbers": nums}
    cls = combine_panels(panel_classes, same=INDETERMINATE)
    used = sorted({c.label for c in case_group} | {reference_label(c) for c in case_group})
    annotations = merge_annotations(notes)
    leaky_set = leaky_labels(index) if leaky is None else set(leaky)
    if leaky_set & set(used):
        annotations.append(LEAKAGE)
        details["interpretation_withheld"] = (
            "LEAKAGE: the lane is not interpreted until the auditor explains it"
        )
    details["used_labels"] = used
    return make_result(lane, subject, cls, panel_classes, annotations, details)


def b1_groups() -> list[list[Cell]]:
    groups: list[list[Cell]] = []
    for arch in ("flat", "learned_tree"):
        for alpha_u in (0.25, 1.0):
            group = [
                c
                for seed in core.INIT_SEEDS
                if (c := find_cell("B1", arch, 16384, alpha_u=alpha_u, seed=seed)) is not None
            ]
            groups.append(group)
    return groups


def analyze(
    index: EvalIndex,
    exposure: int,
    *,
    estimand: str = "matched",
    ceiling_fail: Collection[int] = (),
    leaky: Collection[str] | None = None,
) -> list[ClassResult]:
    """All B1 classes (flat and learned tree, alpha_u in {0.25, 1}); C1 cells are classed against
    their own reference in ``analysis_c`` using ``classify_utilization``."""
    return [
        classify_utilization(
            index, g, exposure, estimand=estimand, ceiling_fail=ceiling_fail, leaky=leaky
        )
        for g in b1_groups()
    ]
