# ruff: noqa: E501
"""P9II analysis (ADR-0019 section 8): assembles the pure functions of ``classes`` over a stage's cells, over the whole study, and loads the inputs from
a run directory. ``analyze_stage`` and ``analyze_study`` take in-memory ``StageData`` (so tests can feed synthetic records of the full registry);
``load_stage`` reads eval records, training records and logs from disk.

Missing cells, failed tasks and failed gates are handled as in P9-I after its fixes (``assess``): a G4, G5 or G6 defect gives ENGINEERING_FAIL; a missing
or failed-to-run Stage 1 cell, or an absent gates record, gives INCOMPLETE and NOT_INTERPRETED (INCOMPLETE) with no class derived (the denominator is never
reduced); a failed G1 or G2 gives NOT_INTERPRETED (classes still returned, marked not interpreted). A LEAKAGE flag is success condition 5 (a failed cell).
Non-finite numbers are read through ``core.number`` and written as strings (``core.jsonable``).
"""

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import classes as C
from . import core
from .train import lines_of

ReadoutKey = int


@dataclass
class CellData:
    """One present cell: its observation at each readout and its training summary at the decisive readout."""

    obs: dict[int, C.Observation]
    summary: C.TrainingSummary | None = None
    status: str = "completed"


@dataclass
class StageData:
    stage: int
    expected: dict[str, list[C.CellKey]]
    cells: dict[tuple[str, int, int], CellData]
    failed_tasks: list[str] = field(default_factory=list)
    unit: int = core.UPDATES

    @property
    def readouts(self) -> tuple[int, ...]:
        return core.stage_readouts(self.stage, self.unit)

    @property
    def decisive(self) -> int:
        return core.decisive_readout(self.stage, self.unit)

    def missing(self) -> list[str]:
        return [f"{arm}/d{d}/j{j}" for arm, keys in self.expected.items() for d, j in keys if (arm, d, j) not in self.cells or self.decisive not in self.cells[(arm, d, j)].obs]


def expected_of(cells: Sequence[core.Cell]) -> dict[str, list[C.CellKey]]:
    out: dict[str, list[C.CellKey]] = {}
    for c in cells:
        out.setdefault(c.arm, []).append((c.draw, c.seed_index))
    return out


@dataclass
class StageResult:
    stage: int
    classes: dict[str, C.ArmClass]
    verdicts: dict[str, dict[C.CellKey, C.CellVerdict]]
    size: C.SizeAnalysis
    details: dict[str, Any]


def a6_references(sd: StageData, readout: int) -> dict[int, C.A6Reference]:
    out: dict[int, C.A6Reference] = {}
    for (arm, d, j), cd in sd.cells.items():
        if arm == "A6" and j == 0 and readout in cd.obs:
            o = cd.obs[readout]
            out[d] = C.A6Reference(o.acc_a, o.acc_b, o.lm_rise)
    return out


def verdicts_at(sd: StageData, readout: int) -> dict[str, dict[C.CellKey, C.CellVerdict]]:
    refs = a6_references(sd, readout)
    out: dict[str, dict[C.CellKey, C.CellVerdict]] = {}
    for (arm, d, j), cd in sd.cells.items():
        if arm in core.LEARNED_ARMS and readout in cd.obs:
            out.setdefault(arm, {})[(d, j)] = C.cell_verdict(cd.obs[readout], refs.get(d))
    return out


def _draw_accuracy(sd: StageData, arm: str) -> dict[int, float]:
    per: dict[int, list[float]] = {}
    for (a, d, _), cd in sd.cells.items():
        o = cd.obs.get(sd.decisive)
        if a == arm and o is not None:
            per.setdefault(d, []).extend([o.acc_a, o.acc_b])
    return {d: sum(v) / len(v) for d, v in per.items()}


def analyze_stage(sd: StageData) -> StageResult:
    """Classes, paired readings, the negative control, annotations and draw-sensitivity estimands of Stage 1 or Stage 2 at the decisive readout."""
    if sd.stage not in core.MIN_EVALUATED:
        raise ValueError("Stage 3 has no classes: use ``scale_probe_of``")
    verdicts = verdicts_at(sd, sd.decisive)
    arms = [a for a in core.LEARNED_ARMS if a in sd.expected]
    classes = {a: C.arm_class(a, sd.stage, verdicts.get(a, {}), sd.expected[a]) for a in arms}
    a0 = verdicts.get("A0", {})
    paired = {a: C.paired_against_a0(a, verdicts.get(a, {}), a0) for a in arms if a != "A0"}
    nc = C.negative_control_failed(classes.get("A1-S"), paired.get("A1-S"))
    size = C.SizeAnalysis(sd.stage, classes, paired, nc)
    refs = a6_references(sd, sd.decisive)
    details: dict[str, Any] = {
        "negative_control_failed": nc,
        "a6": {str(d): {"accuracy_a": r.acc_a, "accuracy_b": r.acc_b, "lm_relative_rise": r.lm_rise, "usable": r.usable} for d, r in sorted(refs.items())},
        "arms": {},
    }
    dense = _draw_accuracy(sd, "A7")
    for arm in arms:
        cells = {k: sd.cells[(arm, *k)] for k in sd.expected[arm] if (arm, *k) in sd.cells}
        summaries = {k: cd.summary for k, cd in cells.items() if cd.summary is not None}
        obs = {k: cd.obs[sd.decisive] for k, cd in cells.items() if sd.decisive in cd.obs}
        entry: dict[str, Any] = {
            "class": classes[arm].label,
            "base_class": classes[arm].cls,
            "counts": {"evaluated": classes[arm].evaluated, "successes": classes[arm].successes, "failures": classes[arm].failures, "lm_flagged_cells": classes[arm].lm_flagged_cells, "missing": classes[arm].missing},
            "lm_capability": {"reduced": classes[arm].lm_reduced, "relative_rises": {f"{d}/{j}": o.lm_rise for (d, j), o in sorted(obs.items())}, "absolute_rise_percent": {f"{d}/{j}": 100.0 * o.lm_rise for (d, j), o in sorted(obs.items())}},
            "categories": C.category_counts(summaries),
            "median_escape_update_escaped_cells_only": C.median([float(s.category.escape) for s in summaries.values() if s.category.escape is not None]),
            "cosine_onset_escape": {f"{d}/{j}": [s.category.cosine_onset, s.category.cosine_escape] for (d, j), s in sorted(summaries.items())},
            "address": C.address_labels(obs, arm),
            "draw_sensitivity": C.draw_sensitivity(arm, verdicts.get(arm, {}), summaries, sd.decisive),
        }
        if arm != "A0":
            p = paired[arm]
            entry["paired_against_a0"] = {"label": p.label, "d": p.d, "x_only": p.x_only, "a0_only": p.a0_only, "pairs": p.pairs, "p_value": p.p_value, "note": "the arm at its better calibrated setting against an untuned A0"}
        if arm == "A2":
            sup = C.supervision_dependent(summaries, {k for k, v in verdicts.get("A2", {}).items() if v.status != C.CELL_NOT_EVALUATED})
            size.supervision_dependent["A2"] = sup["label"] is not None
            entry["supervision_dependent"] = sup
            entry["addresses_remapped_cells"] = sum(1 for k, s in summaries.items() if s.remapped and verdicts.get("A2", {}).get(k, C.CellVerdict(C.FAILED)).status == C.SUCCEEDED)
            a0_move = {k: _a0_path(sd, k, s) for k, s in summaries.items()}
            ratios = [m / a for k, s in summaries.items() if (m := s.movement_after_removal) is not None and (a := a0_move[k]) is not None and a > 0]
            entry["movement_after_removal_relative_to_a0"] = {"median": C.median(ratios), "cells": len(ratios)}
            if "A1" in verdicts:
                entry["paired_against_a1"] = _paired_label(C.paired_against_a0("A2", verdicts.get("A2", {}), verdicts["A1"]))
        if classes[arm].cls == C.RELIABLE and dense:
            entry["dense_comparison"] = C.dense_comparison(_draw_accuracy(sd, arm), dense)
        if sd.stage == 2:
            entry["readout_u"] = _u_readout(sd, arm)
        details["arms"][arm] = entry
    h19 = {"onset_cells": 0, "ratio_cells": 0, "cells": 0}
    for (arm, d, j), cd in sd.cells.items():
        if arm == "A0" and cd.summary is not None:
            h19["cells"] += 1
            h19["onset_cells"] += int(cd.summary.onset_within_256)
            h19["ratio_cells"] += int(math.isfinite(cd.summary.gradient_ratio) and cd.summary.gradient_ratio <= core.H19A_RATIO)
    details["h19a_inputs"] = h19
    return StageResult(sd.stage, classes, verdicts, size, details)


def _paired_label(p: C.Paired) -> dict[str, Any]:
    return {"label": p.label, "d": p.d, "pairs": p.pairs, "p_value": p.p_value, "descriptive": True}


def _a0_path(sd: StageData, key: C.CellKey, summary: C.TrainingSummary) -> float | None:
    a0 = sd.cells.get(("A0", *key))
    if a0 is None or a0.summary is None or summary.u_pre is None:
        return None
    return C.path_after(a0.summary.path, summary.u_pre)


def _u_readout(sd: StageData, arm: str) -> dict[str, Any]:
    """Stage 2: constant-objective arms are classified at U too (ALSO AT MATCHED UPDATES when RELIABLE); A2 and A4 are MID-SCHEDULE and enter no rule."""
    if arm in core.SCHEDULED_ARMS:
        return {"label": C.MID_SCHEDULE, "class": None}
    u = sd.readouts[0]
    cls = C.arm_class(arm, 2, verdicts_at(sd, u).get(arm, {}), sd.expected[arm])
    return {"label": C.ALSO_AT_MATCHED_UPDATES if cls.cls == C.RELIABLE else None, "class": cls.label}


def scale_probe_of(sd: StageData, selected: str) -> dict[str, Any]:
    """Stage 3: the selected arm's two cells against A6 of the same draw (U updates, 32 exposures per fact)."""
    verdicts = verdicts_at(sd, sd.decisive).get(selected, {})
    result = C.scale_probe(verdicts)
    result["selected"] = selected
    result["note"] = "a probe at 32 exposures per fact: it can only be positive or uninformative; a non-positive result is exposure-limited"
    return result


# --- the whole study -------------------------------------------------------------------------------------------------------------
def assess(*, missing: list[str], failed_tasks: list[str], gates: Mapping[str, Any] | None, draw_plan: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Status and interpretability (pure). ENGINEERING_FAIL for a G4, G5 or G6 defect; else INCOMPLETE for a missing or failed Stage 1 cell, a failed task, an absent
    gates record or an exhausted reserve list (a draw plan that is not ``ok``); else COMPLETE. A failed or unrecorded G1 or G2 (G2 on any registered draw) makes the study
    not interpreted. A reserve substitution that section 9 allows is none of these: the replaced draw is recorded in the draw plan as REPLACED BY RESERVE k (audit M5)."""
    defects = [] if gates is None else list(gates.get("g4_defects", []))
    reasons: list[str] = []
    if gates is not None:
        for name in ("g1", "g2", "g4", "g5", "g6"):
            value = gates.get(f"{name}_passed")
            if value is not True:
                reasons.append(f"{name.upper()} failed" if value is False else f"{name.upper()} not recorded")
        for draw, ok in sorted((gates.get("g2_by_draw") or {}).items()):
            if ok is not True:
                reasons.append(f"G2 failed on draw {draw}")
        engineering = bool(defects) or gates.get("g4_passed") is False or gates.get("g5_passed") is False or gates.get("g6_passed") is False
    else:
        engineering = False
    exhausted = draw_plan is not None and draw_plan.get("ok") is False
    incomplete = bool(missing or failed_tasks or gates is None or exhausted)
    status = "ENGINEERING_FAIL" if engineering else ("INCOMPLETE" if incomplete else "COMPLETE")
    replaced = {} if draw_plan is None else {str(k): f"REPLACED BY RESERVE {str(v).rsplit('-', 1)[-1]}" for k, v in (draw_plan.get("replacements") or {}).items()}
    return {
        "status": status, "incomplete": incomplete, "gate_reasons": reasons, "interpretable": not incomplete and not reasons and not engineering, "defects": defects,
        "missing": [*missing, *failed_tasks, *(["gates record"] if gates is None else []), *(["draw plan: the reserve list is exhausted"] if exhausted else [])],
        "replaced_draws": replaced,
    }  # fmt: skip


def stage_status(sd: StageData | None, not_run: str | None, result: StageResult | None) -> str:
    """The status printed with the outcome: the not-run reason, INCOMPLETE (a cell is missing or a task failed), NOT_EVALUATED (A0's class is NOT_EVALUATED) or COMPLETE."""
    if sd is None:
        return not_run or C.NOT_RUN_NO_ARM
    if sd.missing() or sd.failed_tasks:
        return C.INCOMPLETE
    if result is not None and result.classes.get("A0") is not None and result.classes["A0"].cls == C.NOT_EVALUATED:
        return "NOT_EVALUATED"
    return C.COMPLETE


def analyze_study(
    stage1: StageData,
    stage2: StageData | None,
    stage3: StageData | None,
    *,
    stage2_not_run: str | None = None,
    stage3_not_run: str | None = None,
    stage3_selected: str | None = None,
    gates: Mapping[str, Any] | None = None,
    failed_tasks: Sequence[str] = (),
    draw_plan: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Every rule of section 8 over the three stages. ``stage2`` / ``stage3`` are None when the stage did not run (``*_not_run`` names why). When Stage 2 did not
    run, Stage 3 did not run for the same reason (NOT RUN — BUDGET stays NOT RUN — BUDGET; audit m5). Hypotheses B to G are read at 16,384 in the row that says so (row 3);
    without a COMPLETE Stage 2 they print NOT TESTED AT 16,384, never CONTRADICTED, and no interface is carried forward from a Stage 2 that is not COMPLETE (M6)."""
    missing = stage1.missing()
    verdict = assess(missing=missing, failed_tasks=[t for t in failed_tasks if not t.startswith(("train2", "evaluate2", "train3", "evaluate3", "generate-"))] + stage1.failed_tasks, gates=gates, draw_plan=draw_plan)
    out: dict[str, Any] = {"assessment": verdict, "stage1": None, "stage2": None, "stage3": None, "draw_plan": dict(draw_plan) if draw_plan is not None else None}
    if verdict["status"] == "ENGINEERING_FAIL" or verdict["incomplete"]:
        top = C.ENGINEERING_FAIL if verdict["status"] == "ENGINEERING_FAIL" else C.NOT_INTERPRETED_INCOMPLETE
        out["outcome"] = {"outcome": top, "label": top, "row": 1, "arm": None, "missing": verdict["missing"], "reasons": verdict["gate_reasons"], "defects": verdict["defects"], "scope": ["no class, annotation or selection is derived: registered cells, records or gates are missing or defective"]}
        return out
    r1 = analyze_stage(stage1)
    out["stage1"] = r1.details
    r2 = analyze_stage(stage2) if stage2 is not None else None
    s2status = stage_status(stage2, stage2_not_run, r2)
    out["stage2"] = {"status": s2status, **(r2.details if r2 else {})}
    if stage3 is not None and stage3_selected is not None:
        out["stage3"] = {"status": stage_status(stage3, None, None), **scale_probe_of(stage3, stage3_selected)}
    else:
        reason = stage3_not_run or C.NOT_RUN_NO_ARM
        if stage2 is None and stage2_not_run in (C.NOT_RUN_BUDGET, C.INCOMPLETE) and reason == C.NOT_RUN_NO_ARM:
            reason = stage2_not_run
        out["stage3"] = {"status": reason}
    s1status = "NOT_EVALUATED" if r1.classes.get("A0") is not None and r1.classes["A0"].cls == C.NOT_EVALUATED else C.COMPLETE
    outcome = C.study_outcome(r1.size, r2.size if r2 else None, s2status, stage1_status=s1status)
    s2_complete = r2 is not None and s2status == C.COMPLETE
    readings = C.hypothesis_readings(r1.size, r1.details["h19a_inputs"], reading_stage=r2.size if (outcome.row == 3 and s2_complete and r2 is not None) else None, not_tested_status=s2status if (outcome.row == 3 and not s2_complete) else None)
    carried = C.carry_forward(r2.size) if s2_complete and r2 is not None else None
    out["outcome"] = {"outcome": outcome.outcome, "label": outcome.label, "row": outcome.row, "arm": outcome.arm, "stage2_status": s2status, "stage3_status": out["stage3"]["status"], "detail": outcome.detail}
    if not verdict["interpretable"]:
        out["outcome"] = {**out["outcome"], "outcome": C.NOT_INTERPRETED, "label": "NOT_INTERPRETED (" + "; ".join(verdict["gate_reasons"]) + ")", "descriptive_outcome": outcome.label, "row": 1}
    out["hypotheses"] = readings
    out["carried_forward"] = {"arm": carried, "supervision": core.SUPERVISION_LABEL.get(carried or "", None), "recommendation": C.CHANGE_ARCHITECTURE if outcome.row in (7, 8) else None, "stage2_status": s2status}
    return out


# --- loading from a run directory --------------------------------------------------------------------------------------------------
def _point(record: Mapping[str, Any], update: int) -> C.ProbePoint:
    p = record.get("probe") or {}
    return C.ProbePoint(update, int(core.number(p.get("distinct_top1", 0))), core.number(p.get("largest_top1_share", 1.0)), int(core.number(p.get("probe_facts", 0))), core.number(p.get("mean_cosine_different", math.nan)), core.number(p.get("probe_accuracy", math.nan)), core.number(p.get("target_top8_recall", math.nan)))


def load_stage(run_dir: Path, stage: int, cells: Sequence[core.Cell], unit: int = core.UPDATES, failed_tasks: Sequence[str] = ()) -> StageData:
    """Read the eval records (every readout), training records and logs of ``cells``; a cell with a missing or failed record is left out (it is then
    ``missing`` and the study is INCOMPLETE; nothing is imputed)."""
    sd = StageData(stage, expected_of(cells), {}, list(failed_tasks), unit)
    readouts = core.stage_readouts(stage, unit)
    loaded: dict[str, dict[int, dict[str, Any]]] = {}
    for c in cells:
        folder = core.cell_dir(run_dir, c.label)
        records: dict[int, dict[str, Any]] = {}
        for u in readouts:
            path = core.eval_path(run_dir, c.label, u)
            if path.is_file():
                records[u] = core.read_record(path, "eval")
        train = folder / "train.json"
        if len(records) == len(readouts) and train.is_file() and core.read_record(train, "train")["status"] == "completed":
            loaded[c.label] = records
    refs = {c.draw: loaded[c.label][sd.decisive] for c in cells if c.arm == "A6" and c.label in loaded}
    for c in cells:
        if c.label not in loaded:
            continue
        recs = loaded[c.label]
        obs = {u: C.observation_from_eval(r) for u, r in recs.items()}
        summary = None
        if c.arm in core.LEARNED_ARMS:
            folder = core.cell_dir(run_dir, c.label)
            ref = refs.get(c.draw)
            line = math.nan
            if ref is not None:
                ro = C.observation_from_eval(ref)
                line = core.SUCCESS_FRACTION_OF_A6 * (ro.acc_a + ro.acc_b) / 2
            train_rec = core.read_record(folder / "train.json", "train")
            summary = C.summarize_training(c.arm, lines_of(folder / "updates.jsonl"), lines_of(folder / "diagnostics.jsonl"), _point(recs[sd.decisive], sd.decisive), line, u_pre=train_rec["schedule"]["u_pre"], succeeded=True, stage_updates=int(train_rec["matched_updates"]))
        sd.cells[(c.arm, c.draw, c.seed_index)] = CellData(obs, summary)
    return sd
