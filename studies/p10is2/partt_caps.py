# ruff: noqa: E501
"""Projected seconds per registered Part T stage, by ONE shared function (ADR-0025 section 10 items 2 and 3; audit B4, ruling 4).

``projected seconds of a stage = the sum over the plan's tasks of (the sum over the task's kinds of (units of that kind, counted from the PLAN) x (measured seconds per unit of that kind))
+ (the stage's tasks) x (the measured per-process overhead of the stage)``.

The units are counted here from the plan's items and the config's panel sizes, never read from a hand-written file. The rates and the overheads come from the measuring rehearsal's record, which measures every
kind through the registered entry point, in fresh worker processes, with whole-process timing (``required_kinds`` lists them; a record that lacks one cannot give caps and a kind with units and no rate is an
error: nothing is guessed). The caps themselves are the shared ``common.caps.caps_proposal`` of these projections and the charge before the freeze."""

from collections.abc import Mapping, Sequence
from typing import Any

from .common import core
from .common.caps import caps_proposal
from .common.core import StageRefused

CONTROL_RUNS = 6  # control runs per memory arm and capability panel (section 5.2: own, value, code, marker, words, and the unpermuted reading): the auditor's count of the controls' 18,000 greedy items per replicate
TRAINED_TYPES = ("M1", "D1", "M-append", "M-seq", "M-ii", "D-append", "D-seq", "M-joint", "D-joint", "E-table")  # the ten trained types a measuring rehearsal must time on MPS
ORDER_ARMS_N, ORDERS_N, JOINT_N, ETABLE_N, SEP_N = 7, 2, 2, 2, 2


def replicate_units(e: int, s: int, d_con: int) -> dict[str, int]:
    """The greedy decodes of ONE replicate's evaluate task, by kind (audit section 5): full panels of 22 snapshot-pairs, the learned route reads, the controls on their subsamples, D_con, R-icl and R-gloss-icl."""
    pairs = ORDER_ARMS_N * ORDERS_N + JOINT_N + ETABLE_N + ORDERS_N + SEP_N  # the 14 two-stage cells, 2 joint, 2 E-table, M-append@append in each order, M-sep and D-sep = 22
    return {
        "score:plain": pairs * 2 * e, "score:route": ORDERS_N * 2 * e, "score:control": 4 * CONTROL_RUNS * s * ORDERS_N + JOINT_N * CONTROL_RUNS * s, "score:dcon": 2 * 2 * d_con * ORDERS_N, "score:icl": 2 * 2 * e, "router:train": 1,
    }  # fmt: skip


def task_units(items: Mapping[str, Sequence[Mapping[str, Any]]], basis: Mapping[str, int]) -> dict[str, list[dict[str, Any]]]:
    """Per stage, the plan's tasks with their units by kind: ``{"stage": [{"id", "units": {kind: n}}]}``. Counted from the plan's ITEMS (one task per trained cell; one per replicate for the evaluate and combined
    stages; one for the references, the gates, the recomputation, the controls check, the analysis and the report)."""
    e, s, d = int(basis["eval_panel"]), int(basis["control_subsample"]), int(basis["d_con_panel"])
    out: dict[str, list[dict[str, Any]]] = {}
    out["gates"] = [{"id": "gates|all", "units": {"gates:all": 1}}]
    out["train"] = [{"id": c["id"], "units": {f"train:{c['arm']}": int(c["updates"])}} for c in items["train"]]
    reps = sorted({int(i["rep"]) for i in items["train"]})
    out["evaluate"] = [{"id": f"evaluate|r{r}", "units": replicate_units(e, s, d)} for r in reps] + [{"id": "evaluate|reference", "units": {"score:reference": 2 * e}}]
    out["controls"] = [{"id": "controls|check", "units": {"controls:check": 1}}]
    per_rep_combined = {r: sum(1 for i in items["combined"] if i.get("rep") == r) for r in reps}
    out["combined"] = [{"id": f"combined|r{r}", "units": {"combined:arm-cell": per_rep_combined[r]}} for r in reps] + [{"id": "combined|reference", "units": {"combined:arm-cell": 2}}]
    ev = {k: sum(t["units"].get(k, 0) for t in out["evaluate"]) for k in ("score:plain", "score:route", "score:control", "score:dcon", "score:icl", "score:reference", "router:train")}
    out["recompute"] = [{"id": "recompute", "units": {**ev, "combined:arm-cell": sum(t["units"]["combined:arm-cell"] for t in out["combined"])}}]  # it re-scores everything the evaluate and combined stages scored, on CPU
    out["analysis"] = [{"id": "analysis", "units": {"analysis:run": 1}}]
    out["report"] = [{"id": "report", "units": {"report:run": 1}}]
    return out


def required_kinds(items: Mapping[str, Sequence[Mapping[str, Any]]], basis: Mapping[str, int]) -> list[str]:
    """Every kind of every task of the plan: the kinds a measuring rehearsal must have measured (all ten trained types, every scoring kind, the router, the gates, the combined arm-cell, the recomputation's kinds)."""
    return sorted({k for tasks in task_units(items, basis).values() for t in tasks for k in t["units"]})


def project_stage_seconds(items: Mapping[str, Sequence[Mapping[str, Any]]], basis: Mapping[str, int], rates: Mapping[str, float], overhead: Mapping[str, float]) -> dict[str, float]:
    """The one shared function: Σ over tasks of Σ over kinds (units x seconds per unit of the kind) + tasks x the stage's per-process overhead. A kind or a stage with no measurement is an error (never guessed)."""
    out: dict[str, float] = {}
    for stage, tasks in task_units(items, basis).items():
        if stage not in overhead:
            raise StageRefused(f"refused: no measured per-process overhead for stage {stage!r}")
        total = 0.0
        for t in tasks:
            for kind, n in t["units"].items():
                if kind not in rates:
                    raise StageRefused(f"refused: no measured rate for kind {kind!r} (stage {stage!r}): the measuring rehearsal did not measure it")
                total += n * float(rates[kind])
        out[stage] = total + len(tasks) * float(overhead[stage])
    return out


def basis_of(cfg: Mapping[str, Any]) -> dict[str, int]:
    d = cfg["data"]
    return {"eval_panel": int(d["eval_panel"]), "control_subsample": int(d["control_subsample"]), "d_con_panel": int(d["d_con_panel"])}


def counting_projection_seconds(meas: Mapping[str, Any], items: Mapping[str, Sequence[Mapping[str, Any]]]) -> dict[str, Any]:
    """The projected charge of the counting rehearsal (ruling 20), by the shared projection (units x measured seconds per unit of the kind + processes x the stage's measured per-process overhead):

    projected = sum over kinds (subset units of the kind x its measured rate) + sum over stages (processes the rehearsal starts in the stage x its overhead) + 2 x the training stage's overhead (the resumed worker of
    the forced pause and the stage process of the forced identity stop).

    The subset units and the processes per stage are those the measuring rehearsal ran (it runs the same subset through the same entry point). A measuring record that carries no ``subset_units`` (no dry-profile
    rate) is projected as: processes the counting rehearsal starts (per stage, the stage process and one per task of the plan-derived subset) x the stage's overhead + the measured world-build seconds of one
    process per worker, + the same forced extra. The allowance is 2 x the projection."""
    rates, over = meas["rates_seconds_per_unit"], meas["overhead_seconds"]
    units, procs = meas.get("subset_units"), meas.get("subset_processes")
    if units and procs:
        work = sum(float(n) * float(rates[k]) for k, n in units.items())
        overhead = sum(int(procs[s]) * float(over[s]) for s in procs)
        basis = "subset units x rates + processes x overhead"
    else:
        from . import partt_tasks
        from .common import plan as planmod

        plan = planmod.Plan({"kind": "freeze_plan", "study": core.STUDY, "schema": core.SCHEMA, "part": "T", "items": dict(items), "stage_caps": {}}, "T")
        n_proc = {s: 1 + (sum(len(w) for w in partt_tasks.waves_of(s, plan, True)) if s in partt_tasks.TASK_STAGES else 0) for s in items if s in over}
        work = float(meas.get("world_build_seconds", 0.0)) * sum(n_proc.values())
        overhead = sum(n * float(over[s]) for s, n in n_proc.items())
        basis = "processes x overhead + measured world-build seconds"
    forced = 2.0 * float(over["train"])
    return {"seconds": work + overhead + forced, "unit_work_seconds": work, "overhead_seconds": overhead, "forced_events_seconds": forced, "basis": basis}


def counting_allowance_hours(meas: Mapping[str, Any], items: Mapping[str, Sequence[Mapping[str, Any]]]) -> float:
    """``counting_allowance_hours`` = 2 x the projected counting charge, in hours rounded UP to 0.01 h; fixed in the candidate plan BEFORE the counting rehearsal runs (ruling 20)."""
    import math

    return math.ceil(2.0 * counting_projection_seconds(meas, items)["seconds"] / 3600.0 * 100.0 - 1e-9) / 100.0


def proposal_from_record(meas: Mapping[str, Any], items: Mapping[str, Sequence[Mapping[str, Any]]], basis: Mapping[str, int], charge_seconds: float, allowance_seconds: float = 0.0) -> dict[str, float]:
    """The caps by the rule: every registered stage gets 2 x its projection, the total is the charge before the freeze + 2 x all stages (rounded up to 0.01 h), by ``common.caps.caps_proposal``. Refuses a measuring
    record that was not made through the registered entry point (no ``caps_formula``)."""
    if meas.get("caps_formula") != CAPS_FORMULA:
        raise StageRefused(f"refused: the Part T measuring record does not carry caps_formula {CAPS_FORMULA!r}: it was not made through the registered entry point in fresh worker processes")
    proj = project_stage_seconds(items, basis, meas["rates_seconds_per_unit"], meas["overhead_seconds"])
    return dict(caps_proposal(charge_seconds + allowance_seconds, proj))  # total = plan charge + counting allowance + 2 x projected registered stages (ruling 20)


CAPS_FORMULA = "partt-whole-process-v1"


def apply_caps_text(text: str, proposal: Mapping[str, float]) -> str:
    """The config text with each ``<key> = 0.0`` of ``[stage_caps]`` replaced by the proposal and ``caps.provisional`` set false. Refuses unless every key is still exactly 0.0 (caps are written once by code)."""
    import re

    m = re.search(r"(?m)^\[stage_caps\].*$", text)
    if not m:
        raise StageRefused("refused: the config has no [stage_caps] section")
    nxt = re.search(r"(?m)^\[", text[m.end():])
    a, b = m.start(), m.end() + (nxt.start() if nxt else len(text) - m.end())
    body = text[a:b]
    for k, v in proposal.items():
        pat = re.compile(rf"(?m)^{k} = 0\.0(?![0-9])")
        if len(pat.findall(body)) != 1:
            raise StageRefused(f"refused: [stage_caps] does not hold exactly one unset line '{k} = 0.0' (caps already entered?)")
        body = pat.sub(f"{k} = {v}", body)
    out = text[:a] + body + text[b:]
    if out.count("\nprovisional = true") != 1:
        raise StageRefused("refused: the config does not hold exactly one 'provisional = true'")
    return out.replace("\nprovisional = true", "\nprovisional = false")


def zero_caps(cfg: Mapping[str, Any], stages: Sequence[str]) -> list[str]:
    """The registered stages whose cap in the config is 0 (never "uncapped"): the freeze refuses while any."""
    return [s for s in stages if float(cfg["stage_caps"].get(f"{s}_hours", 0.0)) <= 0.0] + (["total"] if float(cfg["stage_caps"].get("total_hours", 0.0)) <= 0.0 else [])


__all__ = ["CAPS_FORMULA", "TRAINED_TYPES", "basis_of", "core", "project_stage_seconds", "proposal_from_record", "replicate_units", "required_kinds", "task_units", "zero_caps"]
