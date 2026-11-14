# ruff: noqa: E501
"""P9 Lane D analysis (package I6): incremental classes.

Specification: ADR-0017 section 8.1 (Lane D G2 family of 4 tests), 8.5 (classes for flat sequential,
flat memory-only and learned tree sequential, each against dense sequential; replay and exact
retrieval reported beside them and entering no class).

With ``a_A`` and ``a_B`` the accuracy on A and B after phase B and ``a_A0`` the accuracy on A after phase
A: classes need ``a_A0 >= 0.5`` (else NOT_EVALUATED); first match wins, per primary panel, both seeds:
1 NOT REPLICATED (panels disagree); 2 NO_NEW_CAPABILITY (a_B < 0.5 x the joint bound's accuracy on B);
3 FORGETTING (a_A < 0.70 a_A0); 4 INCREMENTAL_POSITIVE (a_B >= 0.9 x the bound on B, a_A >= 0.90 a_A0, and
the arm's forgetting a_A0 - a_A at least 0.10 smaller than dense sequential's, whose own a_A0 must be
>= 0.5 else NOT_EVALUATED); 5 INTERMEDIATE. NO ADVANTAGE OVER DENSE is an annotation printed when dense
sequential's forgetting is <= 0.10. Lane D is NOT_EVALUATED if 16,384 slots is TASK_CEILING_FAIL.

The dense floor is read as written inside row 4: rows 2 and 3 do not use the dense arm, so a dense
a_A0 below 0.5 gives NOT_EVALUATED only when neither row matched (PENDING LEAD REVIEW). Seeds: each
seed gives its class by the order above; the seeds give one class if they agree, INTERMEDIATE if they
disagree, NOT_EVALUATED if either seed is not evaluable.

Records: Lane D evaluation streams are named ``lane_d_<panel>_<set>`` with the panel in lower case and
the set ``A`` or ``B`` (``lane_d_stream``): ``lane_d_a_A``, ``lane_d_a_B``, ``lane_d_b_A``, ``lane_d_b_B``
(``EvalRecord.stream`` leaves the spelling open; this is the reading used). A phase-end snapshot is the
cell's own ``core.updates(cell, E)``.

Status: implementation self-checked only. Not independent review, not Astra validation, not human
approval.
"""

from collections.abc import Collection, Mapping
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
    is_chance,
    leaky_labels,
    make_result,
    merge_annotations,
    missing_keys,
)
from .analysis_b import LEAKAGE, combine_seeds
from .core import Cell, ClassResult, EvalIndex, EvalKey

INCREMENTAL_CLASSES = (
    "NOT REPLICATED",
    "NO_NEW_CAPABILITY",
    "FORGETTING",
    "INCREMENTAL_POSITIVE",
    "INTERMEDIATE",
)
CLASSED_ARMS = (
    ("flat", "sequential"),
    ("flat", "memory_only"),
    ("learned_tree", "sequential"),
)
NO_ADVANTAGE = "NO ADVANTAGE OVER DENSE"
LANE_D_STREAM_SETS = ("A", "B")


def lane_d_stream(panel: str, set_name: str) -> str:
    """``lane_d_<panel>_<set>``, for example ``lane_d_a_A`` (panel A, set A)."""
    if panel not in core.PANELS or set_name not in LANE_D_STREAM_SETS:
        raise ValueError("panel is A or B and the set is A or B")
    return f"lane_d_{panel.lower()}_{set_name}"


def d_cell(arch: str, arm: str, seed: int) -> Cell | None:
    block = "D1" if arm == "phaseA" else "D2"
    return find_cell(block, arch, core.LANE_D_SLOTS, seed=seed, lane_d_arm=arm)


def phase_accuracies(index: EvalIndex, label: str, exposure: int, panel: str) -> dict[str, float]:
    """``{"a_A", "a_B"}`` of a D2 cell on ``panel`` and ``{"a_A0"}`` of its D1 cell (the cell it depends
    on; absent for the joint bound), read from the evaluation records of the lane_d streams at the
    phase-end snapshots. Raises ``MissingRecord``."""
    cell = core.parse_label(label)
    update = core.updates(cell, exposure)
    out = {
        "a_A": accuracy_of(get_record(index, label, update, lane_d_stream(panel, "A"))),
        "a_B": accuracy_of(get_record(index, label, update, lane_d_stream(panel, "B"))),
    }
    if cell.depends_on:
        d1 = core.parse_label(cell.depends_on[0])
        out["a_A0"] = accuracy_of(
            get_record(index, d1.label, core.updates(d1, exposure), lane_d_stream(panel, "A"))
        )
    return out


def lane_d_g2(
    index: EvalIndex, panel: str, controls: Mapping[str, Any] | None = None
) -> dict[str, object]:
    """No-memory baseline on sets A and B per primary panel against the 4-test interval
    (``core.chance_interval(4096, core.G2_TESTS_LANE_D)``): ``controls['no_memory']['lane_d_<p>_<S>']`` is
    ``{"correct", "facts"}``. Status 'pass', 'fail' or 'not_reported'."""
    interval = core.chance_interval(core.LANE_D_FACTS, core.G2_TESTS_LANE_D)
    reported = (controls or {}).get("no_memory", {})
    streams: dict[str, object] = {}
    states: list[str] = []
    for s in LANE_D_STREAM_SETS:
        name = lane_d_stream(panel, s)
        entry = reported.get(name) if isinstance(reported, Mapping) else None
        if entry is None:
            states.append("not_reported")
            continue
        inside = is_chance(int(entry["correct"]), int(entry["facts"]), core.G2_TESTS_LANE_D)
        streams[name] = {
            "correct": entry["correct"],
            "facts": entry["facts"],
            "inside_interval": inside,
        }
        states.append("pass" if inside else "fail")
    status = (
        "fail" if "fail" in states else ("not_reported" if "not_reported" in states else "pass")
    )
    return {
        "panel": panel,
        "status": status,
        "interval_correct": [interval.low, interval.high],
        "level": interval.level,
        "streams": streams,
    }


def seed_class(arm: Mapping[str, float], dense: Mapping[str, float], joint_b: float) -> str:
    """Rows 2-5 of ADR 8.5 for one seed on one panel. ``arm`` and ``dense`` hold a_A0, a_A, a_B;
    ``joint_b`` is the joint bound's accuracy on B. NOT_EVALUATED when the arm's a_A0 < 0.5, or when
    rows 2 and 3 do not match and the dense arm's a_A0 < 0.5."""
    a0 = arm["a_A0"]
    if a0 < core.LANE_D_A0_MIN:
        return core.NOT_EVALUATED
    if arm["a_B"] < core.LANE_D_NO_NEW * joint_b:
        return "NO_NEW_CAPABILITY"
    if arm["a_A"] < core.LANE_D_FORGETTING * a0:
        return "FORGETTING"
    if dense["a_A0"] < core.LANE_D_A0_MIN:
        return core.NOT_EVALUATED
    gap = (dense["a_A0"] - dense["a_A"]) - (a0 - arm["a_A"])
    if (
        arm["a_B"] >= core.LANE_D_POSITIVE_B * joint_b
        and arm["a_A"] >= core.LANE_D_POSITIVE_A * a0
        and gap >= core.LANE_D_FORGETTING_GAP - 1e-12
    ):
        return "INCREMENTAL_POSITIVE"
    return core.INTERMEDIATE


def _combine(seed_classes: list[str]) -> str:
    if core.NOT_EVALUATED in seed_classes:
        return core.NOT_EVALUATED
    return combine_seeds(seed_classes)


def _gather(
    index: EvalIndex, arch: str, arm: str, panel: str, exposure: int, seed: int
) -> dict[str, dict[str, float]]:
    cell, dense, joint = (
        d_cell(arch, arm, seed),
        d_cell("dense", "sequential", seed),
        d_cell("flat", "joint", seed),
    )
    if cell is None or dense is None or joint is None:
        raise MissingRecord(f"no registered Lane D cells for {arch}/{arm} seed {seed}")
    return {
        "arm": phase_accuracies(index, cell.label, exposure, panel),
        "dense": phase_accuracies(index, dense.label, exposure, panel),
        "joint": phase_accuracies(index, joint.label, exposure, panel),
    }


def classify_arm_panel(index: EvalIndex, arch: str, arm: str, panel: str, exposure: int) -> str:
    """Classes 2-5 for one panel and one classed arm, with seeds combined (both seeds must satisfy a
    rule). INCOMPLETE if a record is missing."""
    try:
        classes = []
        for seed in core.INIT_SEEDS:
            g = _gather(index, arch, arm, panel, exposure, seed)
            classes.append(seed_class(g["arm"], g["dense"], g["joint"]["a_B"]))
    except MissingRecord:
        return INCOMPLETE
    return _combine(classes)


def arm_needs(arch: str, arm: str, exposure: int) -> list[EvalKey]:
    needs: list[EvalKey] = []
    for seed in core.INIT_SEEDS:
        for cell in (
            d_cell(arch, arm, seed),
            d_cell("dense", "sequential", seed),
            d_cell("flat", "joint", seed),
        ):
            if cell is None:
                continue
            for panel in core.PANELS:
                needs += [
                    (cell.label, core.updates(cell, exposure), lane_d_stream(panel, s))
                    for s in LANE_D_STREAM_SETS
                ]
                if cell.depends_on:
                    d1 = core.parse_label(cell.depends_on[0])
                    needs.append((d1.label, core.updates(d1, exposure), lane_d_stream(panel, "A")))
    return needs


def _optional_arm(
    index: EvalIndex, arch: str, arm: str, seed: int, panel: str, exposure: int
) -> dict[str, float] | None:
    cell = d_cell(arch, arm, seed)
    if cell is None:
        return None
    try:
        return phase_accuracies(index, cell.label, exposure, panel)
    except MissingRecord:
        return None


def classify_arm(
    index: EvalIndex,
    arch: str,
    arm: str,
    exposure: int,
    *,
    ceiling_fail: Collection[int] = (),
    leaky: Collection[str] | None = None,
    controls: Mapping[str, Any] | None = None,
    g2_failed: bool = False,
) -> ClassResult:
    """Class with the NO ADVANTAGE OVER DENSE annotation; replay, exact retrieval and the joint bound
    in ``details`` beside the class (no class of their own). 16,384 slots being TASK_CEILING_FAIL, or a
    failed Lane D G2, gives NOT_EVALUATED; missing records give INCOMPLETE."""
    subject = f"incremental/{arch}/{arm}"
    if core.LANE_D_SLOTS in set(ceiling_fail):
        return make_result(
            "D",
            subject,
            core.NOT_EVALUATED,
            {p: core.NOT_EVALUATED for p in core.PANELS},
            [f"TASK_CEILING_FAIL({core.LANE_D_SLOTS})"],
            {},
        )
    missing = missing_keys(index, arm_needs(arch, arm, exposure))
    if missing:
        return incomplete_result("D", subject, missing)
    panel_classes: dict[str, str] = {}
    notes: dict[str, list[str]] = {}
    details: dict[str, Any] = {"exposure": exposure, "panels": {}}
    used: set[str] = set()
    for panel in core.PANELS:
        seeds: dict[str, str] = {}
        nums: dict[str, Any] = {}
        dense_small_forgetting: list[bool] = []
        for seed in core.INIT_SEEDS:
            g = _gather(index, arch, arm, panel, exposure, seed)
            seeds[str(seed)] = seed_class(g["arm"], g["dense"], g["joint"]["a_B"])
            forgetting = g["arm"]["a_A0"] - g["arm"]["a_A"]
            dense_forgetting = g["dense"]["a_A0"] - g["dense"]["a_A"]
            dense_small_forgetting.append(dense_forgetting <= core.LANE_D_DENSE_FORGETTING_MAX)
            nums[str(seed)] = {
                "arm": g["arm"],
                "forgetting": forgetting,
                "dense_sequential": g["dense"],
                "dense_forgetting": dense_forgetting,
                "joint_bound": g["joint"],
                "beside_the_class_no_class": {
                    "flat_replay": _optional_arm(index, "flat", "replay", seed, panel, exposure),
                    "dense_replay": _optional_arm(index, "dense", "replay", seed, panel, exposure),
                },
            }
            for cell in (
                d_cell(arch, arm, seed),
                d_cell("dense", "sequential", seed),
                d_cell("flat", "joint", seed),
            ):
                if cell is not None:
                    used.add(cell.label)
                    used.update(cell.depends_on)
        panel_classes[panel] = _combine(list(seeds.values()))
        notes[panel] = [NO_ADVANTAGE] if all(dense_small_forgetting) else []
        details["panels"][panel] = {"seed_classes": seeds, "numbers": nums}
    cls = combine_panels(panel_classes)
    if g2_failed:
        details["class_if_g2_passed"] = cls
        cls = core.NOT_EVALUATED
    details["exact_retrieval_append"] = (controls or {}).get("exact_lane_d")
    details["used_labels"] = sorted(used)
    annotations = merge_annotations(notes)
    if g2_failed:
        annotations.append("GATE_FAILED(G2 lane D)")
    leaky_set = leaky_labels(index) if leaky is None else set(leaky)
    if leaky_set & used:
        annotations.append(LEAKAGE)
        details["interpretation_withheld"] = (
            "LEAKAGE: the lane is not interpreted until the auditor explains it"
        )
    return make_result("D", subject, cls, panel_classes, annotations, details)


def analyze(
    index: EvalIndex,
    exposure: int,
    *,
    ceiling_fail: Collection[int] = (),
    leaky: Collection[str] | None = None,
    controls: Mapping[str, Any] | None = None,
) -> list[ClassResult]:
    """All Lane D results for the three classed arms, plus the Lane D G2 entry."""
    g2 = {p: lane_d_g2(index, p, controls) for p in core.PANELS}
    failed = any(v["status"] == "fail" for v in g2.values())
    results = [
        classify_arm(
            index,
            arch,
            arm,
            exposure,
            ceiling_fail=ceiling_fail,
            leaky=leaky,
            controls=controls,
            g2_failed=failed,
        )
        for arch, arm in CLASSED_ARMS
    ]
    status = (
        "fail"
        if failed
        else ("not_reported" if any(v["status"] == "not_reported" for v in g2.values()) else "pass")
    )
    results.append(
        make_result(
            "D",
            "lane_d_g2",
            f"G2_{status.upper()}",
            {p: f"G2_{status.upper()}" for p in core.PANELS},
            ["GATES NOT REPORTED"] if status == "not_reported" else [],
            {"panels": g2},
        )
    )
    return results
