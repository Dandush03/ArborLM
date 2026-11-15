# ruff: noqa: E501
"""P10S0 analysis (ADR-0020 section 8): assembles the pure functions of ``classes`` over the registry, from in-memory ``RunData`` (so tests feed synthetic records of the whole registry) or from a
run directory (``load_run``).

What is derived, in the order of section 8: the A6 references per draw and cell type; per learned arm and cell type the verdict of every cell under S0's criteria and under P9-II's criteria, the two
classes, the paired readings against A0 under both, the replication label against P9-II's class (from the arm-selection record), ADDRESS STABLE, the cross-study consistency label and the pooled count,
the annotations (COLLAPSE-FREE, ADDRESS RECALL, DENSE COMPARISON); the qualified candidate by the preference order; the annotations on the candidate (OVERLOAD, WX, the 65,536 probe); the study outcome
and the hypothesis readings. Missing cells, failed tasks, failed gates, a replaced draw and non-finite values are handled as P9-II's analysis after its fixes: a defect or an unpassed gate gives
ENGINEERING_FAIL / INCOMPLETE with no scientific label and no reduced denominator (outcome row 2); a missing or failed WX or probe cell makes that block INCOMPLETE and leaves Q1's outcome standing.
"""

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from studies.p9ii import classes as p9c
from studies.p9ii.classes import A6Reference, CellKey, CellVerdict, ProbePoint, TrainingSummary

from . import classes as C
from . import core
from .train import lines_of

GATES = ("g1", "g2", "g4", "g5", "g6", "g9", "g10")


@dataclass
class CellData:
    """One present cell: its observation at each readout and its training summary at the decisive readout."""

    obs: dict[int, C.SObservation]
    summary: TrainingSummary | None = None
    status: str = "completed"


@dataclass
class RunData:
    cells: dict[str, CellData]
    arm_selection: Mapping[str, Any]
    failed_tasks: list[str] = field(default_factory=list)
    gates: Mapping[str, Any] | None = None
    draw_plan: Mapping[str, Any] | None = None
    cut3: bool = False
    block_status: dict[str, str] = field(default_factory=dict)  # 'wx' / 'probe': the status the Q1 gate fixed (NOT RUN — BUDGET / MEMORY), if any
    candidate_run: str | None = None  # the candidate the WX and probe blocks were run for (recorded by the Q1 gate)
    frozen_mismatch: list[str] = field(default_factory=list)
    unit: int = core.UPDATES


# --- expected cells and references -------------------------------------------------------------------------------------------------------------------
def expected_q1(cut3: bool) -> dict[tuple[str, str], list[CellKey]]:
    out: dict[tuple[str, str], list[CellKey]] = {}
    for c in core.q1_cells(cut3):
        out.setdefault((c.arm, c.celltype), []).append((c.draw, c.seed_index))
    return out


def label_of(block: str, arm: str, ct: str, draw: int, j: int) -> str:
    return core.make_label(block, arm, ct, draw, j)


def a6_references(run: RunData, ct: str) -> dict[int, A6Reference]:
    out: dict[int, A6Reference] = {}
    decisive = core.CELLTYPES[ct].decisive(run.unit)
    for draw in core.Q1_DRAWS:
        cd = run.cells.get(label_of("Q1", "A6", ct, draw, 0))
        if cd is not None and decisive in cd.obs:
            o = cd.obs[decisive]
            out[draw] = A6Reference(o.acc_a, o.acc_b, o.lm_rise)
    return out


def a6_evaluated(run: RunData, ct: str) -> dict[int, bool]:
    """Per draw: A6 present and at or above the cell type's floor on both panels. A draw whose A6 is missing is not evaluated (and the study is then INCOMPLETE through the missing cell)."""
    refs = a6_references(run, ct)
    return {d: (d in refs and C.A6Ref(*refs[d]).usable_at(ct)) for d in core.Q1_DRAWS}


def _verdicts(run: RunData, block: str, arm: str, ct: str, keys: Sequence[CellKey], readout: int, criteria: str, refs: Mapping[int, A6Reference]) -> dict[CellKey, CellVerdict]:
    out: dict[CellKey, CellVerdict] = {}
    for d, j in keys:
        cd = run.cells.get(label_of(block, arm, ct, d, j))
        if cd is not None and readout in cd.obs and cd.status == "completed":
            out[(d, j)] = C.cell_verdict(cd.obs[readout], refs.get(d), ct, criteria)
    return out


def _rule(ct: str, keys: Sequence[CellKey]) -> str:
    return "20" if len(keys) == 20 else "10"


def _draw_accuracy(run: RunData, block: str, arm: str, ct: str, readout: int) -> dict[int, float]:
    per: dict[int, list[float]] = {}
    for d in core.Q1_DRAWS:
        for j in (0, 1):
            cd = run.cells.get(label_of(block, arm, ct, d, j))
            if cd is not None and readout in cd.obs:
                per.setdefault(d, []).extend([cd.obs[readout].acc_a, cd.obs[readout].acc_b])
    return {d: sum(v) / len(v) for d, v in per.items()}


def p9ii_record(arm_selection: Mapping[str, Any], arm: str, ct: str) -> Mapping[str, Any] | None:
    """P9-II's class record of ``arm`` at the core size of ``ct`` (from the arm-selection record; None at 8K/4K, where P9-II has no cell, and for WX)."""
    size = {"2K/4K": "4096", "8K/16K": "16384"}.get(ct)
    if size is None or core.is_wx(arm):
        return None
    rec = (arm_selection.get("p9ii_classes") or {}).get(arm)
    return None if rec is None else rec.get(size)


def eval_arm(run: RunData, arm: str, ct: str, *, block: str = "Q1", draws: Sequence[int] = core.Q1_DRAWS) -> dict[str, Any] | None:
    """Everything the analysis derives for one learned arm at one cell type; None when the arm has no cell there."""
    keys_all = expected_q1(run.cut3) if block == "Q1" else {(arm, ct): [(d, core.alternating(d)) for d in draws]}
    keys = keys_all.get((arm, ct))
    if keys is None:
        return None
    decisive = core.CELLTYPES[ct].decisive(run.unit)
    refs = a6_references(run, ct)
    rule = _rule(ct, keys)
    s0_v = _verdicts(run, block, arm, ct, keys, decisive, C.S0_CRITERIA, refs)
    p9_v = _verdicts(run, block, arm, ct, keys, decisive, C.P9II_CRITERIA, refs)
    s0_cls, p9_cls = C.arm_class(s0_v, keys, rule), C.arm_class(p9_v, keys, rule)
    obs = {(d, j): run.cells[label_of(block, arm, ct, d, j)].obs[decisive] for (d, j) in s0_v}
    stable = C.address_stable(obs, s0_v)
    p9 = p9ii_record(run.arm_selection, arm, ct)
    out: dict[str, Any] = {
        "arm": arm, "celltype": ct, "rule": rule, "s0": s0_cls, "p9ii_criteria": p9_cls, "failed_conditions": {f"{d}/{j}": list(v.failed_conditions) for (d, j), v in sorted(s0_v.items()) if v.status == C.FAILED},
        "stable": stable, "meets": C.meets_criteria(s0_cls, stable), "p9ii": p9, "replication": C.replication(p9_cls.cls, p9) if ct in core.CORE_CELLTYPES and block == "Q1" else C.NOT_COMPARABLE,
        "added_criterion_failed": C.added_criterion_failed(p9_cls.cls, s0_cls, stable), "verdicts_s0": s0_v, "verdicts_p9ii": p9_v, "observations": obs,
        "lm": {"reduced": s0_cls.lm_reduced, "flagged_cells": s0_cls.lm_flagged_cells},
    }
    p9_draws_failed = p9_cls.draws_failed
    core_q1 = ct in core.CORE_CELLTYPES and block == "Q1"
    if core_q1 and s0_cls.cls == C.NOT_EVALUATED:  # nothing of S0 to pool: the label is not defined
        out["consistency"] = {"label": "NOT DEFINED (S0 NOT_EVALUATED)", "consistent": False, "single_study": False, "p9ii_class": None if p9 is None else p9.get("class"), "failed_draws": p9_draws_failed, "evaluated_draws": p9_cls.draws_evaluated, "pooled_failed": None, "pooled_n": None}
        out["pooled"] = {"available": False, "text": "NOT AVAILABLE (S0 NOT_EVALUATED)"}
    else:
        out["consistency"] = C.consistency(p9, p9_cls.draws_evaluated, p9_draws_failed) if core_q1 else None
        out["pooled"] = C.pooled_line(p9, p9_cls, p9_draws_failed, arm) if core_q1 else {"available": False, "text": "NOT AVAILABLE (S0's protocol at this cell type is not P9-II's)"}
    summaries = {k: run.cells[label_of(block, arm, ct, *k)].summary for k in s0_v if run.cells[label_of(block, arm, ct, *k)].summary is not None}
    never = sum(1 for s in summaries.values() if s is not None and s.category.onset is None)
    out["collapse_free"] = {"k": never, "n": len(summaries), "label": f"{C.COLLAPSE_FREE}: {never} of {len(summaries)} counted cells never had a collapse onset"}
    out["categories"] = p9c.category_counts({k: s for k, s in summaries.items() if s is not None})
    with_first = [s for s in summaries.values() if s is not None and s.first_success is not None]
    out["sustained_success"] = {"cells_with_first_success": len(with_first), "sustained": sum(1 for s in with_first if s.sustained), "label": f"sustained success: {sum(1 for s in with_first if s.sustained)} of {len(with_first)} cells with a first success (descriptive)"}
    if core.base_arm(arm) in core.SUPERVISED:
        out["address_recall"] = p9c.address_labels(obs, core.base_arm(arm)).get("recall")
    if s0_cls.cls == C.RELIABLE and arm in core.LABEL_FREE + core.SUPERVISED and block == "Q1" and ct in core.CORE_CELLTYPES:
        a7 = _draw_accuracy(run, "Q1", "A7", ct, decisive)
        out["dense_comparison"] = p9c.dense_comparison(_draw_accuracy(run, block, arm, ct, decisive), a7)
    if len(core.CELLTYPES[ct].readouts) > 1 and block == "Q1":
        first = core.CELLTYPES[ct].readout_updates(run.unit)[0]
        refs_u = {d: A6Reference(*(lambda o: (o.acc_a, o.acc_b, o.lm_rise))(run.cells[label_of("Q1", "A6", ct, d, 0)].obs[first])) for d in core.Q1_DRAWS if label_of("Q1", "A6", ct, d, 0) in run.cells and first in run.cells[label_of("Q1", "A6", ct, d, 0)].obs}
        at_u = _verdicts(run, block, arm, ct, keys, first, C.S0_CRITERIA, refs_u)
        if at_u:
            cu = C.arm_class(at_u, keys, rule)
            out["class_at_u"] = {"class": cu.label, "label": p9c.MID_SCHEDULE if core.base_arm(arm) == "A2" else p9c.ALSO_AT_MATCHED_UPDATES, "enters_no_rule": True}
    return out


def serialize_eval(e: Mapping[str, Any]) -> dict[str, Any]:
    """The JSON form of ``eval_arm`` (verdict dictionaries are summarized; observations dropped)."""
    out = {k: v for k, v in e.items() if k not in ("verdicts_s0", "verdicts_p9ii", "observations")}
    for key in ("s0", "p9ii_criteria"):
        out[key] = _sclass_dict(e[key])
    out["stable"] = dict(e["stable"])
    return out


def _sclass_dict(c: C.SClass) -> dict[str, Any]:
    return {k: getattr(c, k) for k in c.__dataclass_fields__}


# --- the assessment (outcome row 2) --------------------------------------------------------------------------------------------------------------------
def assess(run: RunData, expected: Mapping[tuple[str, str], Sequence[CellKey]]) -> dict[str, Any]:
    """Defects first, then incompleteness; never a reduced denominator. Harness errors are reported apart from gate failures (section 10.2)."""
    reasons: list[str] = []
    harness: list[str] = []
    g = run.gates
    if g is None:
        reasons.append("gates record missing")
    else:
        for name in GATES:
            value = g.get(f"{name}_passed")
            if value is not True:
                reasons.append(f"{name.upper()} failed" if value is False else f"{name.upper()} not recorded")
        for draw, ok in sorted((g.get("g2_by_draw") or {}).items()):
            if ok is not True:
                reasons.append(f"G2 failed on draw {draw}")
        harness += [str(h) for h in g.get("harness_errors") or []]
    missing: list[str] = []
    for (arm, ct), keys in expected.items():
        decisive = core.CELLTYPES[ct].decisive(run.unit)
        for d, j in keys:
            cd = run.cells.get(label_of("Q1", arm, ct, d, j))
            if cd is None or decisive not in cd.obs or cd.status != "completed":
                missing.append(label_of("Q1", arm, ct, d, j))
    failed = [t for t in run.failed_tasks if not str(t).startswith(("generate", "train-wx", "evaluate-wx", "train-probe", "evaluate-probe"))]  # a failed WX or probe cell makes that block INCOMPLETE; Q1 stands
    plan_bad = run.draw_plan is not None and run.draw_plan.get("ok") is False
    engineering = [*reasons, *[f"HARNESS ERROR (not a gate failure): {h}" for h in harness], *[f"Q1 cell without a record: {m}" for m in missing], *[f"failed task {t}" for t in failed], *[f"frozen/running mismatch: {m}" for m in run.frozen_mismatch], *(["draw plan: the reserve list is exhausted or a reserve failed G1"] if plan_bad else [])]
    replaced = {} if run.draw_plan is None else {str(k): core.replacement_label(str(v)) for k, v in (run.draw_plan.get("replacements") or {}).items()}
    return {"engineering": engineering, "gate_reasons": reasons, "harness_errors": harness, "missing_q1": missing, "failed_tasks": failed, "replaced_draws": replaced, "interpretable": not engineering}


# --- Q2 blocks ------------------------------------------------------------------------------------------------------------------------------------------
def _block_cells(block: str, candidate: str | None, run: RunData) -> list[core.Cell]:
    if candidate is None or candidate not in core.CANDIDATE_ARMS:
        return []
    return core.wx_cells(candidate) if block == "wx" else core.probe_cells(candidate)


def wx_block(run: RunData, candidate: str | None, selection_row: int) -> dict[str, Any]:
    """WX of the candidate on the Q1 draws (section 6.2): the class under S0's criteria and ADDRESS STABLE at 2K/4K and 8K/16K (10-cell types), the status of the block."""
    status = _q2_status("wx", candidate, selection_row, run)
    out: dict[str, Any] = {"status": status, "candidate": candidate, "celltypes": {}}
    if candidate is None or candidate not in core.CANDIDATE_ARMS or status in (C.NOT_RUN_NO_CANDIDATE, C.NOT_RUN_BUDGET, C.NOT_RUN_MEMORY):
        return out
    arm = f"WX-{candidate}"
    for ct in core.CORE_CELLTYPES:
        keys = [(d, core.alternating(d)) for d in core.Q1_DRAWS]
        refs = a6_references(run, ct)
        decisive = core.CELLTYPES[ct].decisive(run.unit)
        v = _verdicts(run, "WX", arm, ct, keys, decisive, C.S0_CRITERIA, refs)
        if not v:
            continue
        cls = C.arm_class(v, keys, "10")
        obs = {k: run.cells[label_of("WX", arm, ct, *k)].obs[decisive] for k in v}
        stable = C.address_stable(obs, v)
        out["celltypes"][ct] = {"class": cls, "stable": stable, "meets": C.meets_criteria(cls, stable), "failed_conditions": {f"{d}/{j}": list(x.failed_conditions) for (d, j), x in sorted(v.items()) if x.status == C.FAILED}, "verdicts": v}
    if status == C.COMPLETE and any(c["class"].cls == C.NOT_EVALUATED for c in out["celltypes"].values()):
        out["status"] = "NOT_EVALUATED"
    return out


def probe_block(run: RunData, candidate: str | None, selection_row: int) -> dict[str, Any]:
    """The 65,536 probe: the candidate and A6 at 32K/64K on draws 11-13; counts only (k of 3 succeed), NOT_EVALUATED if any draw's A6 is below 0.90."""
    status = _q2_status("probe", candidate, selection_row, run)
    out: dict[str, Any] = {"status": status, "candidate": candidate}
    if candidate is None or candidate not in core.CANDIDATE_ARMS or status in (C.NOT_RUN_NO_CANDIDATE, C.NOT_RUN_BUDGET, C.NOT_RUN_MEMORY):
        return out
    ct = "32K/64K"
    decisive = core.CELLTYPES[ct].decisive(run.unit)
    refs: dict[int, A6Reference] = {}
    for d in core.PROBE_DRAWS:
        cd = run.cells.get(label_of("PR", "A6", ct, d, 0))
        if cd is not None and decisive in cd.obs:
            o = cd.obs[decisive]
            refs[d] = A6Reference(o.acc_a, o.acc_b, o.lm_rise)
    keys = [(d, 0) for d in core.PROBE_DRAWS]
    v = _verdicts(run, "PR", candidate, ct, keys, decisive, C.S0_CRITERIA, refs)
    evaluated = {d: (d in refs and C.A6Ref(*refs[d]).usable_at(ct)) for d in core.PROBE_DRAWS}
    result = C.probe_status(v, evaluated)
    out.update({k: v for k, v in result.items() if k != "status"})
    out["a6_evaluated"] = evaluated
    out["verdicts"] = v
    if status == C.COMPLETE and result["status"] == "NOT_EVALUATED":
        out["status"] = "NOT_EVALUATED"
    return out


def _q2_status(block: str, candidate: str | None, selection_row: int, run: RunData) -> str:
    if selection_row != 4 or candidate is None or candidate not in core.CANDIDATE_ARMS:
        return C.NOT_RUN_NO_CANDIDATE
    fixed = run.block_status.get(block)
    if fixed in (C.NOT_RUN_BUDGET, C.NOT_RUN_MEMORY):
        return fixed
    cells = _block_cells(block, candidate, run)
    decisive = {c.label: c.ct.decisive(run.unit) for c in cells}
    absent = [c.label for c in cells if c.label not in run.cells or decisive[c.label] not in run.cells[c.label].obs or run.cells[c.label].status != "completed"]
    failed = [t for t in run.failed_tasks if str(t).startswith((f"train-{block}", f"evaluate-{block}"))]
    return C.INCOMPLETE if absent or failed else C.COMPLETE


# --- the whole study ---------------------------------------------------------------------------------------------------------------------------------------
def analyze(run: RunData) -> dict[str, Any]:
    """Every rule of section 8 over the registry."""
    sel = run.arm_selection
    expected = expected_q1(run.cut3)
    assessment = assess(run, expected)
    not_started = bool(sel["mapping"]["not_started"])
    out: dict[str, Any] = {"assessment": assessment, "arm_selection": {"mapping_printed": sel["mapping_printed"], "fourth_arm_printed": sel["fourth_arm_printed"], "table_row": sel["mapping"]["table_row"], "c4": sel["mapping"]["c4"], "candidates": sel["candidates"], "calibrated": sel["calibrated"]}, "cut3": run.cut3}
    if not_started or assessment["engineering"]:
        outcome = C.study_outcome(not_started=not_started, engineering=assessment["engineering"], inconclusive=False, selection={"candidate": None, "qualified_4096_only": None})
        out["outcome"] = {"row": outcome.row, "outcome": outcome.outcome, "label": outcome.label, "arm": None, "detail": outcome.detail, "scope": ["no class, annotation or selection is derived: registered cells, records or gates are missing or defective"] if not not_started else ["S0 did not start: no audited P9-II calibration record"]}
        return out
    evals: dict[str, dict[str, dict[str, Any]]] = {}
    for arm in core.CORE_LEARNED_ARMS:
        for ct in core.ARM_CELLTYPES[arm]:
            e = eval_arm(run, arm, ct)
            if e is not None:
                evals.setdefault(arm, {})[ct] = e
    a6ok = {ct: a6_evaluated(run, ct) for ct in core.CELLTYPES if ct != "32K/64K"}
    paired_s0: dict[str, dict[str, p9c.Paired]] = {}
    paired_p9: dict[str, dict[str, p9c.Paired]] = {}
    for arm in ("A1", "A2", "A5-D"):
        for ct in core.CORE_CELLTYPES:
            paired_s0.setdefault(arm, {})[ct] = C.paired(arm, evals[arm][ct]["verdicts_s0"], evals["A0"][ct]["verdicts_s0"])
            paired_p9.setdefault(arm, {})[ct] = C.paired(arm, evals[arm][ct]["verdicts_p9ii"], evals["A0"][ct]["verdicts_p9ii"])
    for ct in core.CORE_CELLTYPES:
        paired_a2_a1 = C.paired("A2", evals["A2"][ct]["verdicts_s0"], evals["A1"][ct]["verdicts_s0"])
        evals["A2"][ct]["d_against_a1"] = {"d": paired_a2_a1.d, "p_value": paired_a2_a1.p_value, "descriptive": True}
    for arm in ("A5-D",):
        if "8K/4K" in evals.get(arm, {}):
            evals[arm]["8K/4K"]["paired_against_a0"] = _paired_dict(C.paired(arm, evals[arm]["8K/4K"]["verdicts_s0"], evals["A0"]["8K/4K"]["verdicts_s0"]))
    selection = C.select_candidate({a: {ct: {"meets": e["meets"], "consistency": e["consistency"]} for ct, e in per.items() if ct in core.CORE_CELLTYPES} for a, per in evals.items()})
    inconclusive = C.q1_inconclusive(a6ok["2K/4K"])
    outcome = C.study_outcome(not_started=False, engineering=[], inconclusive=inconclusive, selection=selection, evals={a: {ct: e for ct, e in per.items()} for a, per in evals.items()})
    candidate = selection["candidate"] if outcome.row == 4 else None
    wx = wx_block(run, candidate, outcome.row)
    probe = probe_block(run, candidate, outcome.row)
    overload_cls = evals[candidate]["8K/4K"]["s0"] if candidate in evals and "8K/4K" in evals[candidate] else None
    overload = C.overload_label(candidate, overload_cls)
    wx_results = {ct: (v["class"], v["stable"]) for ct, v in wx["celltypes"].items()}
    record_length = C.record_length_label(wx_results, wx["status"])
    replication = {arm: {ct: evals[arm][ct]["replication"] for ct in core.CORE_CELLTYPES} for arm in core.CORE_LEARNED_ARMS}
    a0_failed = evals["A0"]["8K/16K"]["s0"].failures if "A0" in evals else None
    readings = C.hypothesis_readings(
        classes={a: {ct: e["s0"] for ct, e in per.items()} for a, per in evals.items()}, paired_s0=paired_s0, replication_labels=replication, outcome=outcome, candidate=candidate, overload=overload,
        record_length=record_length, probe=probe if probe["status"] in (C.COMPLETE, "NOT_EVALUATED") and "successes" in probe else None,
        probe_a6_evaluated=bool(probe.get("a6_evaluated") and all(probe["a6_evaluated"].values())), a0_failed_cells_8k16k=a0_failed,
    )  # fmt: skip
    out["a6"] = {ct: {str(d): {"accuracy_a": r.acc_a, "accuracy_b": r.acc_b, "lm_relative_rise": r.lm_rise, "evaluated": a6ok[ct][d]} for d, r in sorted(a6_references(run, ct).items())} for ct in a6ok}
    out["arms"] = {a: {ct: serialize_eval(e) for ct, e in per.items()} for a, per in evals.items()}
    out["paired"] = {a: {ct: {"s0": _paired_dict(paired_s0[a][ct]), "p9ii": _paired_dict(paired_p9[a][ct])} for ct in core.CORE_CELLTYPES} for a in paired_s0}
    out["selection"] = {k: v for k, v in selection.items()}
    out["outcome"] = {"row": outcome.row, "outcome": outcome.outcome, "label": outcome.label, "arm": outcome.arm, "scope": outcome.scope, "detail": outcome.detail}
    out["overload"] = overload
    out["record_length"] = {"label": record_length, "status": wx["status"], "celltypes": {ct: {"class": _sclass_dict(v["class"]), "stable": v["stable"], "meets": v["meets"], "failed_conditions": v["failed_conditions"]} for ct, v in wx["celltypes"].items()}}
    out["probe"] = {k: v for k, v in probe.items() if k != "verdicts"}
    out["q2_status"] = {"wx": wx["status"], "probe": probe["status"]}
    out["p9ii_negative_control"] = sel["p9ii_negative_control"]
    out["hypotheses"] = readings
    out["replacements"] = assessment["replaced_draws"]
    out["a0_failed_cells_8k16k"] = a0_failed
    return out


def _paired_dict(p: p9c.Paired) -> dict[str, Any]:
    return {"label": p.label, "d": p.d, "x_only": p.x_only, "a0_only": p.a0_only, "x_successes": p.x_successes, "a0_successes": p.a0_successes, "pairs": p.pairs, "p_value": p.p_value}


# --- loading from a run directory --------------------------------------------------------------------------------------------------------------------------------
def _point(record: Mapping[str, Any], update: int) -> ProbePoint:
    p = record.get("probe") or {}
    return ProbePoint(update, int(core.number(p.get("distinct_top1", 0))), core.number(p.get("largest_top1_share", 1.0)), int(core.number(p.get("probe_facts", 0))), core.number(p.get("mean_cosine_different", math.nan)), core.number(p.get("probe_accuracy", math.nan)), core.number(p.get("target_top8_recall", math.nan)))


def load_run(run_dir: Path, arm_selection: Mapping[str, Any], *, cut3: bool = False, unit: int = core.UPDATES, failed_tasks: Sequence[str] = (), gates: Mapping[str, Any] | None = None, draw_plan: Mapping[str, Any] | None = None, block_status: Mapping[str, str] | None = None, candidate_run: str | None = None, frozen_mismatch: Sequence[str] = ()) -> RunData:
    """Read the eval records (every readout), training records and logs of every registered cell present in ``run_dir``; a cell with a missing or failed record is left out (it is then missing and
    the study INCOMPLETE; nothing is imputed). Cells of the WX and probe blocks are read for every candidate that has them."""
    cells: dict[str, core.Cell] = {c.label: c for c in core.q1_cells(False)}
    for cand in core.CANDIDATE_ARMS:
        cells.update({c.label: c for c in [*core.wx_cells(cand), *core.probe_cells(cand)]})
    data: dict[str, CellData] = {}
    for label, c in cells.items():
        folder = core.cell_dir(run_dir, label)
        readouts = c.ct.readout_updates(unit)
        recs = {u: core.read_record(core.eval_path(run_dir, label, u), "eval") for u in readouts if core.eval_path(run_dir, label, u).is_file()}
        train = folder / "train.json"
        if len(recs) != len(readouts) or not train.is_file() or core.read_record(train, "train")["status"] != "completed":
            continue
        data[label] = CellData({u: C.observation_from_eval(r) for u, r in recs.items()}, None)
    for label, cd in data.items():
        c = cells[label]
        if not c.learned:
            continue
        folder = core.cell_dir(run_dir, label)
        decisive = c.ct.decisive(unit)
        block = "PR" if c.block == "PR" else c.block
        ref_label = label_of("PR" if block == "PR" else "Q1", "A6", c.celltype, c.draw, 0)
        ref = data.get(ref_label)
        line = math.nan
        if ref is not None and decisive in ref.obs:
            ro = ref.obs[decisive]
            line = core.SUCCESS_FRACTION_OF_A6 * (ro.acc_a + ro.acc_b) / 2
        train_rec = core.read_record(folder / "train.json", "train")
        rec_dec = core.read_record(core.eval_path(run_dir, label, decisive), "eval")
        cd.summary = p9c.summarize_training(c.base, lines_of(folder / "updates.jsonl"), lines_of(folder / "diagnostics.jsonl"), _point(rec_dec, decisive), line, u_pre=train_rec["schedule"]["u_pre"], succeeded=True, stage_updates=int(train_rec["matched_updates"]))
    return RunData(data, arm_selection, list(failed_tasks), gates, draw_plan, cut3, dict(block_status or {}), candidate_run, list(frozen_mismatch), unit)
