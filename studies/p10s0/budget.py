# ruff: noqa: E501
"""P10S0 budgets and projections (ADR-0020 section 10): the rehearsal matrix (every distinct (arm, cell type, phase) of the Q1 matrix, WX and the 32K/64K cell for every arm that can
still be the candidate, A6 at 32K/64K), the rates a rehearsal measures (run twice: alone and under twelve busy processes; the larger rate is used), the projection of a block (measured seconds
per update x planned updates, PLUS the per-task start-up time the registered tasks pay again, plus the measured evaluation with the read swap, arranged in rounds of six), the headroom rule
under reading A of the re-check's R2 with the cuts in their registered order, the memory rule (the rehearsal peak, evaluation peaks included, at most 1.5 GiB per worker; else NOT RUN — MEMORY), and
the cap table written by the freeze procedure (one entry per block and configuration). Everything here is a pure function of its inputs; every number it returns is ANALYTICAL (a projection from
measured rates), never a measurement of a result, and none is an efficiency claim or a speedup.

Defects of P9-II's pre-freeze audit not repeated here: the projection includes the task start-up time (B1); the memory rule includes the evaluation peaks and the pool's task peak (M2); the caps are
per configuration (M3), a table written by a procedure and never typed (M7, m12).
"""

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, NamedTuple

from . import core

Item = tuple[str, str, str]  # (arm, celltype, phase)
NOT_RUN_BUDGET = "NOT RUN — BUDGET"
NOT_RUN_MEMORY = "NOT RUN — MEMORY"
CAP_FLOOR_SECONDS = 60.0  # the floor of the caps of stages not rehearsed at real size (gates, analysis, report, generation); stated, not measured


class CapMissing(ValueError):
    """The frozen cap table has no entry for a block or a configuration: the stage refuses."""


def phases_of(arm: str) -> tuple[str, ...]:
    return ("pre", "post") if core.base_arm(arm) == "A2" else ("main",)


def rehearsal_items(candidates: Sequence[str] = core.CANDIDATE_ARMS) -> list[Item]:
    """Every distinct (arm, cell type, phase): the Q1 matrix (A2 before and after its switch), WX and the 32K/64K cell for every arm that can still be the candidate, and A6 at 32K/64K."""
    items: list[Item] = []
    for arm, cts in core.ARM_CELLTYPES.items():
        items += [(arm, ct, ph) for ct in cts for ph in phases_of(arm)]
    items += [(f"WX-{c}", ct, "main") for c in candidates for ct in core.CORE_CELLTYPES]
    items += [(c, "32K/64K", "main") for c in candidates]
    items.append(("A6", "32K/64K", "main"))
    return items


def item_label(item: Item) -> str:
    arm, ct, phase = item
    return f"REH-{arm}-{core.CELLTYPES[ct].token}-{phase}"


def parse_item_label(label: str) -> Item:
    body = label[len("REH-") :]
    arm_ct, phase = body.rsplit("-", 1)
    for c in core.CELLTYPES.values():
        if arm_ct.endswith("-" + c.token):
            return (arm_ct[: -len(c.token) - 1], c.name, phase)
    raise ValueError(f"not a rehearsal item label: {label!r}")


@dataclass(frozen=True)
class Rate:
    """Measured rehearsal rates of one item. ``task_overhead_seconds`` is the pool task's wall seconds minus the timed training and evaluation (process start-up, data generation, backbone
    loading), paid again by every registered task. The peaks are those of the training, the sampled training, the evaluation and the pool task."""

    seconds_per_update: float
    peak_rss_bytes: int
    sampled_rss_bytes: int
    evaluation_seconds: float
    task_overhead_seconds: float = 0.0
    evaluation_peak_rss_bytes: int = 0
    task_peak_rss_bytes: int = 0


Rates = dict[Item, Rate]


def rates_from_records(train: Sequence[Mapping[str, Any]], evaluation: Sequence[Mapping[str, Any]], tasks: Mapping[str, Mapping[str, float]] | None = None) -> Rates:
    """Rates from the rehearsal's whitelisted records (``rehearsal.json`` and ``rehearsal_evaluate.json``, matched by label) and the pool's per-task ``{label: {"seconds", "peak_rss_bytes"}}``
    keyed by the item label. The overhead is the task's seconds minus the training and evaluation seconds, never negative."""
    eval_by_label = {str(r["label"]): r for r in evaluation}
    out: Rates = {}
    for r in train:
        item = (str(r["arm"]), str(r["celltype"]), str(r["phase"]))
        e = eval_by_label.get(str(r["label"]))
        e_seconds = float(e["evaluation_wall_seconds"]) if e is not None else math.nan
        task = (tasks or {}).get(item_label(item))
        overhead = max(0.0, float(task["seconds"]) - float(r["wall_seconds"]) - e_seconds) if task is not None and math.isfinite(e_seconds) else 0.0
        out[item] = Rate(float(r["seconds_per_update"]), int(r["peak_rss_bytes"]), int(r["sampled_rss_bytes"]), e_seconds, overhead, int(e["peak_rss_bytes"]) if e is not None else 0, int(task["peak_rss_bytes"]) if task is not None else 0)
    return out


def merge_rates(first: Rates, second: Rates) -> Rates:
    """The two rehearsals (alone, and under twelve busy processes): the larger measured rate of each item, field by field (section 10.3). An item missing from one run is taken from the other."""
    out: Rates = {}
    for item in {*first, *second}:
        a, b = first.get(item), second.get(item)
        if a is None or b is None:
            out[item] = a or b  # type: ignore[assignment]
            continue
        out[item] = Rate(
            max(a.seconds_per_update, b.seconds_per_update), max(a.peak_rss_bytes, b.peak_rss_bytes), max(a.sampled_rss_bytes, b.sampled_rss_bytes), max(a.evaluation_seconds, b.evaluation_seconds),
            max(a.task_overhead_seconds, b.task_overhead_seconds), max(a.evaluation_peak_rss_bytes, b.evaluation_peak_rss_bytes), max(a.task_peak_rss_bytes, b.task_peak_rss_bytes),
        )  # fmt: skip
    return out


def missing_items(rates: Rates, candidates: Sequence[str] = core.CANDIDATE_ARMS) -> list[Item]:
    return [i for i in rehearsal_items(candidates) if i not in rates or not math.isfinite(rates[i].evaluation_seconds)]


# --- projections --------------------------------------------------------------------------------------------------------------------------------
def _rate(rates: Rates, arm: str, ct: str, phase: str) -> float:
    return rates[(arm, ct, phase)].seconds_per_update


def cell_training_seconds(cell: core.Cell, rates: Rates, hyper: core.Hyper = core.HYPER, unit: int = core.UPDATES) -> float:
    """Measured seconds per update x the cell's planned updates, plus the task's start-up time. A2: its phase 1 at the 'pre' rate and the rest at the 'post' rate."""
    total = cell.ct.updates(unit)
    phase = phases_of(cell.arm)[-1]
    overhead = rates[(cell.arm, cell.celltype, phase)].task_overhead_seconds
    if cell.base == "A2":
        pre = min(total, int(core.schedule_for(cell.arm, cell.celltype, hyper, unit).u_pre or 0))
        return pre * _rate(rates, cell.arm, cell.celltype, "pre") + (total - pre) * _rate(rates, cell.arm, cell.celltype, "post") + overhead
    return total * _rate(rates, cell.arm, cell.celltype, "main") + overhead


def cell_evaluation_seconds(cell: core.Cell, rates: Rates, unit: int = core.UPDATES) -> float:
    """One measured full evaluation (with the read swap) per readout, plus the task's start-up time."""
    rate = rates[(cell.arm, cell.celltype, phases_of(cell.arm)[-1])]
    return len(cell.ct.readouts) * rate.evaluation_seconds + rate.task_overhead_seconds


def makespan(seconds: Sequence[float], workers: int = core.WORKERS) -> float:
    """Rounds of ``workers`` cells: the cells sorted by decreasing time, each round as long as its longest cell."""
    ordered = sorted(seconds, reverse=True)
    return float(sum(ordered[i] for i in range(0, len(ordered), workers)))


class Projection(NamedTuple):
    cells: int
    training_seconds: float
    evaluation_seconds: float
    total_seconds: float
    rounds: int


def block_projection(cells: Sequence[core.Cell], rates: Rates, hyper: core.Hyper = core.HYPER, unit: int = core.UPDATES, workers: int = core.WORKERS) -> Projection:
    """Training makespan plus evaluation makespan of a block's cells, in rounds of ``workers`` (analytical, from measured rates, task start-up included)."""
    train = makespan([cell_training_seconds(c, rates, hyper, unit) for c in cells], workers)
    ev = makespan([cell_evaluation_seconds(c, rates, unit) for c in cells], workers)
    return Projection(len(cells), train, ev, train + ev, math.ceil(len(cells) / workers))


def block_cells(block: str, key: str | None = None) -> list[core.Cell]:
    """The cells of a block and its configuration: ``q1`` (key ``full`` or ``cut3``), ``wx`` and ``probe`` (key = the candidate arm)."""
    if block == "q1":
        if key not in ("full", "cut3"):
            raise ValueError("q1 has the configurations 'full' and 'cut3'")
        return core.q1_cells(key == "cut3")
    if block == "wx":
        return core.wx_cells(str(key))
    if block == "probe":
        return core.probe_cells(str(key))
    raise ValueError(f"unknown block {block!r}")


def block_configurations() -> list[tuple[str, str]]:
    return [("q1", "full"), ("q1", "cut3"), *[("wx", c) for c in core.CANDIDATE_ARMS], *[("probe", c) for c in core.CANDIDATE_ARMS]]


def block_items(block: str, key: str) -> list[Item]:
    """The rehearsal items a block's configuration uses (for its memory check)."""
    return sorted({(c.arm, c.celltype, ph) for c in block_cells(block, key) for ph in phases_of(c.arm)})


def projection_table(rates: Rates, hyper: core.Hyper = core.HYPER, unit: int = core.UPDATES) -> dict[str, dict[str, Any]]:
    """The projection of every block configuration (recorded at the freeze, so a gate reads a table and computes nothing new)."""
    out: dict[str, dict[str, Any]] = {}
    for block, key in block_configurations():
        p = block_projection(block_cells(block, key), rates, hyper, unit)
        out[f"{block}:{key}"] = {"cells": p.cells, "training_seconds": p.training_seconds, "evaluation_seconds": p.evaluation_seconds, "total_seconds": p.total_seconds, "rounds": p.rounds}
    return out


def most_expensive(table: Mapping[str, Mapping[str, Any]], block: str, candidates: Sequence[str] = core.CANDIDATE_ARMS) -> tuple[str, float]:
    """The most expensive possible candidate of a block among the arms that can still be the candidate (section 10.3 as revised in revision 4): (arm, projected total seconds)."""
    arm = max(candidates, key=lambda c: float(table[f"{block}:{c}"]["total_seconds"]))
    return arm, float(table[f"{block}:{arm}"]["total_seconds"])


# --- the headroom rule and the cuts (section 10.4, reading A) -------------------------------------------------------------------------------------------
def holds(charged_seconds: float, projected_seconds: Sequence[float], cap_seconds: float | None = None) -> bool:
    """(hours already charged) + 2 x (rehearsed projection of the stages evaluated) <= 16 hours."""
    cap = core.CAP_HOURS * 3600.0 if cap_seconds is None else cap_seconds
    return all(math.isfinite(p) for p in projected_seconds) and charged_seconds + core.HEADROOM * float(sum(projected_seconds)) <= cap


class PreQ1Decision(NamedTuple):
    action: str  # 'full' | 'cut3' | 'stop'
    status: str | None
    charged_seconds: float
    required_seconds: float
    cut: int | None


def pre_q1_decision(charged_seconds: float, before_q1_seconds: float, q1_full_seconds: float, q1_cut3_seconds: float, cap_seconds: float | None = None, reserve_seconds: float = 0.0) -> PreQ1Decision:
    """Before Q1 the rule is evaluated on Q1 and on the stages before Q1 that have not yet run (stages already run count once, as hours already charged). If it does not hold, cut 3 (the second seed at
    8K/16K dropped) is applied; if it still does not hold, item 4: nothing registered is run and the matter returns to the human lead. ``reserve_seconds`` is the rehearsed time of the analysis and report
    stages (the lead's ruling on M6): it counts, doubled like every other remaining stage, as part of what is still to run, so that a block is not started if it would leave less than that."""
    full = holds(charged_seconds, [before_q1_seconds, q1_full_seconds, reserve_seconds], cap_seconds)
    if full:
        return PreQ1Decision("full", None, charged_seconds, core.HEADROOM * (before_q1_seconds + q1_full_seconds + reserve_seconds), None)
    if holds(charged_seconds, [before_q1_seconds, q1_cut3_seconds, reserve_seconds], cap_seconds):
        return PreQ1Decision("cut3", None, charged_seconds, core.HEADROOM * (before_q1_seconds + q1_cut3_seconds + reserve_seconds), 3)
    return PreQ1Decision("stop", NOT_RUN_BUDGET, charged_seconds, core.HEADROOM * (before_q1_seconds + q1_cut3_seconds + reserve_seconds), None)


class PostQ1Decision(NamedTuple):
    wx: bool
    probe: bool
    wx_status: str | None
    probe_status: str | None
    cuts: tuple[int, ...]
    charged_seconds: float


def post_q1_decision(charged_seconds: float, wx_seconds: float, probe_seconds: float, cap_seconds: float | None = None, reserve_seconds: float = 0.0) -> PostQ1Decision:
    """After the Q1 gate the rule is evaluated on WX and the probe with the actual candidate's rehearsed rates and the hours charged; cut 1 (drop the probe) and then cut 2 (drop WX) are applied as
    needed. Both dropped blocks print NOT RUN — BUDGET."""
    if holds(charged_seconds, [wx_seconds, probe_seconds, reserve_seconds], cap_seconds):
        return PostQ1Decision(True, True, None, None, (), charged_seconds)
    if holds(charged_seconds, [wx_seconds, reserve_seconds], cap_seconds):
        return PostQ1Decision(True, False, None, NOT_RUN_BUDGET, (1,), charged_seconds)
    return PostQ1Decision(False, False, NOT_RUN_BUDGET, NOT_RUN_BUDGET, (1, 2), charged_seconds)


def multiple_thresholds(table_hours: Mapping[str, float], other_hours: float = core.PROJECTED_OTHER_HOURS) -> dict[str, float]:
    """Context only: the multiple m of the slowest P9-I rates up to which each plan fits, (16 - 2 x other) / (2 x the block's six-worker hours) (section 10.4 bullets)."""
    return {k: (core.CAP_HOURS - core.HEADROOM * other_hours) / (core.HEADROOM * v) for k, v in table_hours.items() if v > 0}


# --- memory (section 10.4) ----------------------------------------------------------------------------------------------------------------------------
def peak_of(rate: Rate) -> int:
    return max(rate.peak_rss_bytes, rate.sampled_rss_bytes, rate.evaluation_peak_rss_bytes, rate.task_peak_rss_bytes)


def memory_check(rates: Rates, block: str, key: str, limit_bytes: int = core.REHEARSAL_PEAK_LIMIT_BYTES) -> dict[str, Any]:
    """The memory rule of a block's configuration: its largest rehearsal peak (training, sampled, evaluation and the pool task) must be at most 1.5 GiB per worker (so 2x fits 3 GiB per worker and six
    workers at 2x fit 18 GiB); else the block is NOT RUN — MEMORY and nothing is changed to make it fit. A missing item fails the check."""
    items = block_items(block, key)
    absent = [item_label(i) for i in items if i not in rates]
    peak = max((peak_of(rates[i]) for i in items if i in rates), default=0)
    ok = bool(not absent and peak <= limit_bytes and 2 * peak <= core.RSS_WORKER_BYTES and 2 * peak * core.WORKERS <= core.RSS_AGGREGATE_BYTES)
    return {"block": block, "key": key, "peak_rss_bytes": peak, "limit_bytes": limit_bytes, "missing_items": absent, "ok": ok, "status": None if ok else NOT_RUN_MEMORY}


def memory_table(rates: Rates, limit_bytes: int = core.REHEARSAL_PEAK_LIMIT_BYTES) -> dict[str, dict[str, Any]]:
    return {f"{b}:{k}": memory_check(rates, b, k, limit_bytes) for b, k in block_configurations()}


# --- caps (one table, written by the freeze procedure) ---------------------------------------------------------------------------------------------
GATES_EXTRA_DRAWS = core.N_DRAWS - 1  # the rehearsal-draw gates cover one draw; the registered gates verify and run G2 on thirteen


def gates_measured_seconds(gates_wall_seconds: float, gates_per_draw_seconds: float) -> float:
    """The registered gates' measured time: the rehearsal-draw gates (which include one draw's rebuild, hash check and G2) plus twelve more such draws (the lead's ruling on M8)."""
    return gates_wall_seconds + GATES_EXTRA_DRAWS * gates_per_draw_seconds


def caps_table(rates: Rates, *, gates_wall_seconds: float, gates_per_draw_seconds: float, analysis_wall_seconds: float, report_wall_seconds: float, generate_wall_seconds: float, hyper: core.Hyper = core.HYPER, unit: int = core.UPDATES, floor_seconds: float = CAP_FLOOR_SECONDS) -> dict[str, Any]:
    """The frozen cap table (``studies/p10s0/freeze/stage_caps.json``): each block cap is twice the rehearsed projection (task start-up included) of what it bounds, one entry per block configuration
    (Q1 full and under cut 3; WX and the probe for each arm that can still be the candidate), so a block's cap is that of the configuration its gate selects. Gates, generation, analysis and report are not
    rehearsed at real size: twice a measured time with the stated floor."""
    if gates_per_draw_seconds <= 0:
        raise ValueError("the gates cap needs the rehearsal draw's measured per-draw time (13 draws x 3 fact sets in the registered gates)")
    gates_measured = gates_measured_seconds(gates_wall_seconds, gates_per_draw_seconds)
    table = projection_table(rates, hyper, unit)

    def entry(p: Mapping[str, Any]) -> dict[str, float]:
        return {"train": core.HEADROOM * float(p["training_seconds"]), "evaluate": core.HEADROOM * float(p["evaluation_seconds"])}

    return {
        "rule": "each block cap = 2 x the rehearsed projection (task start-up included) of its configuration; gates, generation, analysis and report: 2 x a measured time with the stated floor",
        "floor_seconds": floor_seconds,
        "generate": max(floor_seconds, core.HEADROOM * generate_wall_seconds), "gates": max(floor_seconds, core.HEADROOM * gates_measured),
        "measured": {"gates": gates_measured, "gates_rehearsal_draw": gates_wall_seconds, "gates_per_draw": gates_per_draw_seconds, "analysis": analysis_wall_seconds, "report": report_wall_seconds, "generate": generate_wall_seconds, "reserve_analysis_report": analysis_wall_seconds + report_wall_seconds},
        "q1": {k.split(":")[1]: entry(v) for k, v in table.items() if k.startswith("q1:")},
        "wx": {k.split(":")[1]: entry(v) for k, v in table.items() if k.startswith("wx:")},
        "probe": {k.split(":")[1]: entry(v) for k, v in table.items() if k.startswith("probe:")},
        "analysis": max(floor_seconds, core.HEADROOM * analysis_wall_seconds), "report": max(floor_seconds, core.HEADROOM * report_wall_seconds),
    }  # fmt: skip


def cap_for(table: Mapping[str, Any], stage: str, key: str | None = None) -> Any:
    """The cap of ``stage`` (``generate``, ``gates``, ``q1``, ``wx``, ``probe``, ``analysis``, ``report``); ``key`` is the configuration (Q1: ``full`` or ``cut3``; WX and the probe: the candidate arm).
    A stage or configuration with no entry raises ``CapMissing`` (the stage refuses)."""
    if stage not in table:
        raise CapMissing(f"the frozen cap table has no entry for {stage!r}")
    value = table[stage]
    if stage in ("q1", "wx", "probe"):
        if key is None or key not in value:
            raise CapMissing(f"the frozen cap table has no entry for {stage} {key!r}")
        value = value[key]
    return value


def cost_differences(rates: Rates) -> dict[str, dict[str, float]]:
    """Measured seconds per update that one mechanism adds (descriptive; no efficiency claim; never a speedup): L_addr (A1 - A0), L_div (A5-D - A0), WX against its base arm, per cell type where both
    were rehearsed."""
    pairs = {"L_addr (A1 - A0)": (("A1", "main"), ("A0", "main")), "L_div (A5-D - A0)": (("A5-D", "main"), ("A0", "main")), "WX query (WX-A5-D - A5-D)": (("WX-A5-D", "main"), ("A5-D", "main")), "WX query (WX-A1 - A1)": (("WX-A1", "main"), ("A1", "main")), "A2 phase 1 (pre - post)": (("A2", "pre"), ("A2", "post"))}
    out: dict[str, dict[str, float]] = {}
    for name, ((a, pa), (b, pb)) in pairs.items():
        for ct in core.CELLTYPES:
            if (a, ct, pa) in rates and (b, ct, pb) in rates:
                out.setdefault(name, {})[ct] = rates[(a, ct, pa)].seconds_per_update - rates[(b, ct, pb)].seconds_per_update
    return out
