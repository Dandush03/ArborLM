# ruff: noqa: E501
"""P9I classes (ADR-0017 Part I, section I.8): pure functions from measurements to the raw class, the
class at a size, the annotations and the selection outcome. Nothing here reads a file, trains or
evaluates a model; ``stages.analyze`` turns eval records into ``Measure`` tables and calls it.

Every rule uses accuracy. "Chance" means inside the G2 interval: an accuracy is "above chance" when it is
above the upper end of that interval for the panel's fact count (``Measure.chance_high``).

Readings fixed here where the section is silent (all reported, none changes a threshold):

* eta = accuracy(arm) / accuracy(R1) at the same size, seed, parent and panel; with an R1 accuracy of 0
  eta is +infinity for a positive accuracy and 0 for a zero accuracy.
* The B102 replicate is classified with rows 2-4 of step 1 (the NOT_EVALUATED row is about B101 seeds);
  the class at 16,384 becomes INTERMEDIATE when the B102 raw class is FAILS on either panel and the B101
  class is INTERFACE_WORKS. A missing replicate leaves the class unchanged and is reported
  (``b102_present`` False); the analysis stage then marks the study INCOMPLETE.
* MODEL_STORES_FACTS is checked after the B102 rule, on BB only, from BB-0's accuracy above chance at the
  size on either B101 seed or panel.
* The dense comparison is made for the class INTERFACE_WORKS or INTERFACE_PARTIAL only, exactly as written;
  MODEL_STORES_FACTS (derived from INTERFACE_WORKS) is therefore NOT COMPARED. A dense accuracy of 0 gives
  r = +infinity; the dense arms other than D7 (for W7) and BB-D (for BB) have no pair.
* Backbone contrast: ratios with a zero state-arm accuracy are +infinity for a positive embedding-arm
  accuracy and 1 when both are zero.
"""

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from . import core

# raw classes (step 1) and classes at a size (step 2)
NOT_EVALUATED, WORKS, PARTIAL, FAILS = "NOT_EVALUATED", "WORKS", "PARTIAL", "FAILS"
RAW_CLASSES = (NOT_EVALUATED, WORKS, PARTIAL, FAILS)
NOT_REPLICATED, INTERMEDIATE = "NOT REPLICATED", "INTERMEDIATE"
INTERFACE_WORKS, INTERFACE_PARTIAL, INTERFACE_FAILS = "INTERFACE_WORKS", "INTERFACE_PARTIAL", "INTERFACE_FAILS"
MODEL_STORES_FACTS = "MODEL_STORES_FACTS"
SIZE_CLASSES = (
    NOT_EVALUATED,
    NOT_REPLICATED,
    INTERMEDIATE,
    INTERFACE_WORKS,
    INTERFACE_PARTIAL,
    INTERFACE_FAILS,
    MODEL_STORES_FACTS,
)
# annotations
BEATS_DENSE, DENSE_SUFFICES, NOT_COMPARED = "BEATS DENSE", "DENSE SUFFICES", "NOT COMPARED"
BACKBONE_HURTS = "BACKBONE HURTS ADDRESSING"
BACKBONE_NOTHING = "BACKBONE ADDS NOTHING"
BACKBONE_CONTRIBUTES = "BACKBONE CONTRIBUTES"
BACKBONE_MIXED = "BACKBONE CONTRAST MIXED"
LM_DEGRADED = "LANGUAGE MODELLING DEGRADED"
# selection outcomes
INCONCLUSIVE = "INCONCLUSIVE"
SELECTED_BB, SELECTED_A4, SELECTED_W7 = "BB", "A4", "W7"
NONE_SELECTED = "NO_INTERFACE_SELECTED"
NOT_INTERPRETED = "NOT_INTERPRETED"
NOT_INTERPRETED_INCOMPLETE = "NOT_INTERPRETED (INCOMPLETE)"
OUTCOMES = (INCONCLUSIVE, SELECTED_BB, SELECTED_A4, SELECTED_W7, NONE_SELECTED, NOT_INTERPRETED, NOT_INTERPRETED_INCOMPLETE)

SEEDS_B101 = core.INIT_SEEDS
PANELS = core.PANELS
Key = tuple[str, int, tuple[int, int], int, str]  # (arm, slots, parent, seed, panel)


@dataclass(frozen=True)
class Measure:
    """What the rules read from one cell and panel: accuracy on trained facts, the upper end of the G2
    interval for that panel's fact count (as an accuracy), and whether value permutation and disabling
    both gave chance (inside the interval)."""

    accuracy: float
    chance_high: float
    dependence_chance: bool = True


def measure_from_panel(panel_record: Mapping[str, Any]) -> Measure:
    """``Measure`` of one panel of an eval record (``evaluate.evaluate_stream`` output)."""
    interval = panel_record["chance_interval"]
    facts = int(panel_record["facts"])
    return Measure(
        accuracy=float(panel_record["accuracy"]),
        chance_high=float(interval[1]) / facts,
        dependence_chance=bool(panel_record["memory_dependence_chance"]),
    )


def measures_from_eval(records: Mapping[str, Mapping[str, Any]]) -> dict[Key, Measure]:
    """``{label: eval record}`` -> the ``Key -> Measure`` table (arm, slots, parent, seed, panel)."""
    out: dict[Key, Measure] = {}
    for record in records.values():
        for panel, p in record["panels"].items():
            key = (record["arm"], int(record["slots"]), (int(record["parent"][0]), int(record["parent"][1])), int(record["seed"]), panel)
            out[key] = measure_from_panel(p)
    return out


def _acc(table: Mapping[Key, Measure], arm: str, slots: int, parent: tuple[int, int], seed: int, panel: str) -> Measure | None:
    return table.get((arm, slots, parent, seed, panel))


def ratio(numerator: float, denominator: float) -> float:
    """accuracy ratio; +infinity for a positive numerator over zero, 1 for 0 / 0 (reading above)."""
    if denominator > 0:
        return numerator / denominator
    return math.inf if numerator > 0 else 1.0


# --- step 1: raw class --------------------------------------------------------------------------------------------
def size_not_evaluated(table: Mapping[Key, Measure], slots: int) -> bool:
    """True when R1 accuracy is below 0.5 at ``slots`` in any B101 seed or panel (step 1 row 1, step 0).
    A size with no R1 measurement is not evaluated either (nothing to compare with)."""
    values = [_acc(table, "R1", slots, core.PRIMARY_PARENT, s, p) for s in SEEDS_B101 for p in PANELS]
    if any(v is None for v in values):
        return True
    return any(v is not None and v.accuracy < core.R1_NOT_EVALUATED for v in values)


def raw_class(
    arm: Measure,
    r1: Measure | None,
    *,
    size_not_eval: bool = False,
) -> str:
    """Step 1, first match wins: NOT_EVALUATED (the size's R1 is below 0.5); WORKS (accuracy >= 0.5, eta >=
    0.90, value permutation and disabling give chance); PARTIAL (above chance and >= 0.25); FAILS."""
    if size_not_eval:
        return NOT_EVALUATED
    eta = ratio(arm.accuracy, r1.accuracy) if r1 is not None else math.nan
    if arm.accuracy >= core.WORKS_ACCURACY and eta >= core.WORKS_ETA and arm.dependence_chance:
        return WORKS
    if arm.accuracy > arm.chance_high and arm.accuracy >= core.PARTIAL_ACCURACY:
        return PARTIAL
    return FAILS


def raw_classes(table: Mapping[Key, Measure], arm: str, slots: int) -> dict[tuple[int, str], str]:
    """Raw class of ``arm`` at ``slots`` for each B101 seed and panel (all four pairs; a missing
    measurement gives no entry)."""
    not_eval = size_not_evaluated(table, slots)
    out: dict[tuple[int, str], str] = {}
    for seed in SEEDS_B101:
        for panel in PANELS:
            m = _acc(table, arm, slots, core.PRIMARY_PARENT, seed, panel)
            if m is None:
                continue
            out[(seed, panel)] = raw_class(m, _acc(table, "R1", slots, core.PRIMARY_PARENT, seed, panel), size_not_eval=not_eval)
    return out


# --- step 2: class at the size --------------------------------------------------------------------------------------
def class_at_size(raws: Mapping[tuple[int, str], str]) -> str:
    """Step 2, first match wins: NOT_EVALUATED; NOT REPLICATED (for a B101 seed the raw classes on Panels
    A and B differ); INTERMEDIATE (the two B101 seeds give different raw classes); else INTERFACE_<raw>."""
    if len(raws) != len(SEEDS_B101) * len(PANELS):
        raise ValueError("the class at a size needs all four seed-panel raw classes")
    if any(v == NOT_EVALUATED for v in raws.values()):
        return NOT_EVALUATED
    if any(raws[(s, "A")] != raws[(s, "B")] for s in SEEDS_B101):
        return NOT_REPLICATED
    per_seed = {raws[(s, "A")] for s in SEEDS_B101}
    if len(per_seed) > 1:
        return INTERMEDIATE
    return {WORKS: INTERFACE_WORKS, PARTIAL: INTERFACE_PARTIAL, FAILS: INTERFACE_FAILS}[next(iter(per_seed))]


def b102_raw_classes(table: Mapping[Key, Measure], arm: str, slots: int) -> dict[str, str] | None:
    """Raw classes of the B102 replicate (seed 1801) on each panel, rows 2-4 of step 1 (R1 of the same
    parent); None when the replicate (or its R1) is absent."""
    out: dict[str, str] = {}
    for panel in PANELS:
        m = _acc(table, arm, slots, core.REPLICATE_PARENT, core.INIT_SEEDS[0], panel)
        r1 = _acc(table, "R1", slots, core.REPLICATE_PARENT, core.INIT_SEEDS[0], panel)
        if m is None or r1 is None:
            return None
        out[panel] = raw_class(m, r1)
    return out


@dataclass(frozen=True)
class SizeResult:
    """Class of one arm at one size with the numbers behind it."""

    arm: str
    slots: int
    cls: str
    raw: dict[str, str]  # "seed/panel" -> raw class
    b102: dict[str, str] | None
    b102_present: bool
    b102_demoted: bool
    model_stores_facts: bool | None  # BB only


def classify(table: Mapping[Key, Measure], arm: str, slots: int) -> SizeResult:
    """Steps 1 and 2, then the B102 rule (where a replicate is registered and present), then, for BB,
    MODEL_STORES_FACTS."""
    raws = raw_classes(table, arm, slots)
    cls = class_at_size(raws)
    b102 = b102_raw_classes(table, arm, slots)
    demoted = False
    if b102 is not None and cls == INTERFACE_WORKS and any(v == FAILS for v in b102.values()):
        cls, demoted = INTERMEDIATE, True
    stores: bool | None = None
    if arm == "BB":
        stores = False
        if cls == INTERFACE_WORKS:
            for seed in SEEDS_B101:
                for panel in PANELS:
                    z = _acc(table, "BB-0", slots, core.PRIMARY_PARENT, seed, panel)
                    if z is not None and z.accuracy > z.chance_high:
                        stores = True
            if stores:
                cls = MODEL_STORES_FACTS
    return SizeResult(arm, slots, cls, {f"{s}/{p}": v for (s, p), v in raws.items()}, b102, b102 is not None, demoted, stores)


# --- annotations (printed per size; they never change a class) -------------------------------------------------------------
DENSE_PAIR = {"W7": "D7", "BB": "BB-D"}
BACKBONE_PAIRS = (("E7", "W7"), ("A4E", "A4"))
BACKBONE_SIZE = 16384


def dense_comparison(table: Mapping[Key, Measure], arm: str, slots: int, arm_class: str) -> dict[str, Any] | None:
    """BEATS DENSE (smallest of the four paired ratios >= 1.10) or DENSE SUFFICES; NOT COMPARED when the
    arm's class is not INTERFACE_WORKS / INTERFACE_PARTIAL or the arm has no dense comparator (A4, A4E,
    and every arm but W7 and BB); None when the dense arm does not run at this size."""
    dense = DENSE_PAIR.get(arm)
    if dense is None:
        return {"label": NOT_COMPARED, "reason": "no dense comparator", "ratios": None}
    values = [(s, p, _acc(table, arm, slots, core.PRIMARY_PARENT, s, p), _acc(table, dense, slots, core.PRIMARY_PARENT, s, p)) for s in SEEDS_B101 for p in PANELS]
    if any(d is None for _, _, _, d in values):
        return None
    if arm_class not in (INTERFACE_WORKS, INTERFACE_PARTIAL):
        return {"label": NOT_COMPARED, "reason": f"class {arm_class}", "ratios": None}
    ratios = {f"{s}/{p}": ratio(a.accuracy, d.accuracy) for s, p, a, d in values if a is not None and d is not None}
    smallest = min(ratios.values())
    return {"label": BEATS_DENSE if smallest >= core.BEATS_DENSE_RATIO else DENSE_SUFFICES, "reason": None, "ratios": ratios, "smallest": smallest}


def backbone_contrast(table: Mapping[Key, Measure], embedding_arm: str, state_arm: str, classes: Mapping[str, str]) -> dict[str, Any] | None:
    """Four-way contrast at 16,384 for a pair (embedding arm, state arm): HURTS if all four ratios
    embedding / state are >= 1.03, else ADDS NOTHING if all >= 0.97, else CONTRIBUTES if all < 0.97, else
    MIXED. None (not printed) when both arms are INTERFACE_FAILS or a measurement is missing."""
    if classes.get(embedding_arm) == INTERFACE_FAILS and classes.get(state_arm) == INTERFACE_FAILS:
        return None
    ratios: dict[str, float] = {}
    for s in SEEDS_B101:
        for p in PANELS:
            e = _acc(table, embedding_arm, BACKBONE_SIZE, core.PRIMARY_PARENT, s, p)
            a = _acc(table, state_arm, BACKBONE_SIZE, core.PRIMARY_PARENT, s, p)
            if e is None or a is None:
                return None
            ratios[f"{s}/{p}"] = ratio(e.accuracy, a.accuracy)
    values = list(ratios.values())
    if all(r >= core.BACKBONE_HURTS for r in values):
        label = BACKBONE_HURTS
    elif all(r >= core.BACKBONE_NOTHING for r in values):
        label = BACKBONE_NOTHING
    elif all(r < core.BACKBONE_NOTHING for r in values):
        label = BACKBONE_CONTRIBUTES
    else:
        label = BACKBONE_MIXED
    return {"label": label, "pair": [embedding_arm, state_arm], "ratios": ratios}


def language_modelling_annotation(relative_rises: Mapping[int, float]) -> dict[str, Any]:
    """LANGUAGE MODELLING DEGRADED if the next-byte loss rises by more than 5% relative on either B101 seed
    (``relative_rises[seed]``); otherwise not degraded. Carried with BB; never blocks selection."""
    degraded = any(r > core.LM_DEGRADED_RELATIVE for r in relative_rises.values())
    return {"label": LM_DEGRADED if degraded else "LANGUAGE MODELLING PRESERVED", "degraded": degraded, "relative_rises": {str(k): v for k, v in relative_rises.items()}}


# --- the selection rule (section I.8.3) -----------------------------------------------------------------------------
SCOPE_ENCODER = "addressed by a memory-side encoder of the input; the frozen backbone contributes nothing to addressing"
SCOPE_W7_LIMIT = "W7 is told the record length (seven positions)"
SCOPE_BB = "a jointly trained block-0 attention formed the query for this synthetic task within U updates; it does not show that a language model reliably communicates what it needs"
SCOPE_A4_W7_SYSTEM = "ADR-0017 would test a memory with its own input encoder, a different system from the P4-P8 memory addressed by the backbone's state"


@dataclass(frozen=True)
class Selection:
    """Outcome of the selection rule. ``step`` is 0..4 (the step that decided); ``inconclusive_sizes`` lists
    the sizes that triggered step 0 with their reasons."""

    outcome: str
    step: int
    inconclusive_sizes: dict[int, str]
    scope: list[str]


def select(
    classes: Mapping[str, Mapping[int, str]],
    size_status: Mapping[int, str | None],
    *,
    sizes: tuple[int, ...] = core.SLOTS_BY_SIZE,
    backbone_contrast_labels: Mapping[str, str | None] | None = None,
) -> Selection:
    """Section I.8.3. ``classes[arm][size]`` the class at the size (BB, A4, W7); ``size_status[size]`` is
    ``TASK_CEILING_FAIL``, ``ORACLE_QUERY_FAIL``, ``NOT_EVALUATED`` or None for a size that ran.
    0. any size with a status -> INCONCLUSIVE AT that size (not step 4);
    1. BB INTERFACE_WORKS at all sizes -> BB; 2. else A4; 3. else W7 (told the record length);
    4. else none selected, ADR-0017 stays blocked on this backbone."""
    bad = {s: str(size_status[s]) for s in sizes if size_status.get(s)}
    if bad:
        return Selection(INCONCLUSIVE, 0, bad, ["no interface is selected; the human lead decides"])
    for step, arm, outcome in ((1, "BB", SELECTED_BB), (2, "A4", SELECTED_A4), (3, "W7", SELECTED_W7)):
        if all(classes.get(arm, {}).get(s) == INTERFACE_WORKS for s in sizes):
            return Selection(outcome, step, {}, scope(outcome, backbone_contrast_labels or {}))
    return Selection(NONE_SELECTED, 4, {}, ["no tested interface reached INTERFACE_WORKS at all three sizes within U updates; ADR-0017 stays blocked on this backbone"])


def scope(outcome: str, contrast: Mapping[str, str | None]) -> list[str]:
    """The scope statement the selected interface carries (section I.2 and I.8.3). For W7 and A4 the
    encoder statement holds unless that arm's backbone contrast is BACKBONE CONTRIBUTES."""
    if outcome == SELECTED_BB:
        return [SCOPE_BB]
    pair = "E7/W7" if outcome == SELECTED_W7 else "A4E/A4"
    lines = [] if contrast.get(pair) == BACKBONE_CONTRIBUTES else [SCOPE_ENCODER]
    if outcome == SELECTED_W7:
        lines.append(SCOPE_W7_LIMIT)
    lines.append(SCOPE_A4_W7_SYSTEM)
    return lines


# --- the whole analysis ----------------------------------------------------------------------------------------------------
def analyze_classes(
    table: Mapping[Key, Measure],
    lm: Mapping[tuple[str, int, int], float],
    size_status: Mapping[int, str | None],
    *,
    sizes: tuple[int, ...] = core.SLOTS_BY_SIZE,
) -> dict[str, Any]:
    """Classes, annotations and the selection from a measurement table. ``lm[(arm, slots, seed)]`` is the
    relative rise of the backbone's next-byte loss of a BB cell (B101 seeds). Sizes with a status
    (``size_status``) or with R1 below 0.5 are NOT_EVALUATED for every arm."""
    status = dict(size_status)
    for s in sizes:
        if not status.get(s) and size_not_evaluated(table, s):
            status[s] = NOT_EVALUATED
    results: dict[str, dict[int, SizeResult]] = {}
    annotations: dict[str, dict[int, dict[str, Any]]] = {}
    for arm in core.RECORD_CLASSIFIED_ARMS:
        for s in sizes:
            if status.get(s) in (core.TASK_CEILING_FAIL, core.ORACLE_QUERY_FAIL):
                continue  # the size is not run
            if not all(_acc(table, arm, s, core.PRIMARY_PARENT, seed, p) for seed in SEEDS_B101 for p in PANELS):
                continue  # the arm does not run at this size, or its cells are missing
            results.setdefault(arm, {})[s] = classify(table, arm, s)
    flat_classes = {arm: {s: r.cls for s, r in per.items()} for arm, per in results.items()}
    for arm, per in results.items():
        for s, r in per.items():
            note: dict[str, Any] = {}
            dense = dense_comparison(table, arm, s, r.cls)
            if dense is not None:
                note["dense_comparison"] = dense
            if arm == "BB":
                rises = {seed: lm[(arm, s, seed)] for seed in SEEDS_B101 if (arm, s, seed) in lm}
                if rises:
                    note["language_modelling"] = language_modelling_annotation(rises)
            annotations.setdefault(arm, {})[s] = note
    contrasts: dict[str, dict[str, Any] | None] = {}
    for emb, state in BACKBONE_PAIRS:
        contrasts[f"{emb}/{state}"] = backbone_contrast(table, emb, state, {a: flat_classes.get(a, {}).get(BACKBONE_SIZE, "") for a in (emb, state)}) if BACKBONE_SIZE in sizes else None
    labels = {pair: (c["label"] if c else None) for pair, c in contrasts.items()}
    selection = select(flat_classes, status, sizes=sizes, backbone_contrast_labels=labels)
    return {
        "classes": {arm: {str(s): r.cls for s, r in per.items()} for arm, per in results.items()},
        "details": {arm: {str(s): r.__dict__ for s, r in per.items()} for arm, per in results.items()},
        "annotations": {arm: {str(s): n for s, n in per.items()} for arm, per in annotations.items()},
        "backbone_contrast": contrasts,
        "size_status": {str(s): status.get(s) for s in sizes},
        "selection": {"outcome": selection.outcome, "step": selection.step, "inconclusive_sizes": {str(k): v for k, v in selection.inconclusive_sizes.items()}, "scope": selection.scope},
    }
