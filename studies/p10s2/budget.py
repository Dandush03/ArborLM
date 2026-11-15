# ruff: noqa: E501
"""Budgets, projections, the rehearsal rung rule, the cap extension and the memory rule (ADR-0022 sections 13.2, 13.3).

Every number returned here is analytical (a projection from rates a rehearsal measured), never a measurement of a result and never an efficiency claim. Lessons carried from P9-II (pre-freeze audit
B1, M1-M3): a registered task is a fresh process, so every projection includes the per-task start-up overhead; the memory rule reads the training, evaluation, recomputation and whole-task peaks, not
the training peak alone; and every stage has a cap per design configuration (a stage whose configuration has no entry refuses).

Rehearsal rule, fixed in the ADR. Let P be the hours already charged at the end of the rehearsal and R(n, U) the registered run projected from the rehearsal's measured rates for n replicates and U
updates. The design is the first of: four replicates U = 2,000; three replicates U = 2,000; four replicates U = 1,000; three replicates U = 1,000; for which P + 2 R <= the cap (36 hours unless raised);
none: the run is not started (NOT STARTED: BUDGET) and the lead returns to the human lead. R contains training, every scoring of the registered run, the timing benchmark, the second gates stage on
registered seeds and the independent recomputation of every score. For U = 1,000 every store-type cell uses the slower of the rates measured at L = 4 and L = 12.

Cap extension (the human lead's decision, section 18; the lead's limits on its own use). The cap stays 36 hours. At the rehearsal's headroom check only, before any registered seed of S2 is observed, if
rung 1 does not satisfy P + 2R <= 36, the cap is raised to the smallest whole number of hours at which rung 1 satisfies it, up to 72 (the ceiling). If rung 1 would need more than 72, the rung rule
applies in its registered order against 72. The raise is recorded once, in the study ledger and in the freeze folder; its amount is recomputed here from the rehearsal record (the rates) and P, never
typed; the mechanism refuses to act after any registered seed has been observed (ledger, seed record or a committed plan in the repository history).

Revision after the audits (2026-11-15): P is read from the one study ledger; the analysis and report time rehearsed on synthetic records of the whole registry is inside R (so the headroom rule doubles it);
every store-type group, E-table included, has a rate at each rehearsed read layer and U = 1,000 takes the slower; the recomputation projection includes the timing row.
"""

import json
import math
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from arborlm.io import atomic_write

from . import core
from .ledger import Ledger
from .registry import replicate_cells

NOT_STARTED_BUDGET = "NOT STARTED: BUDGET"
B = core.CFG["budget"]
GIB = 2**30
COMBINED_CELLS = 10  # arm-cells scored on C1 and C2 per replicate: M-append-frozen 2, M-ii 2, M-joint 1, L-joint 1, L-seq 2, M-i-separate 1, L-sep 1 (addendum section 10); charged inside R with its recomputation
CAP_FLOOR_SECONDS = 60.0  # the floor for stages that are not rehearsed at real size (analysis, report); stated, not measured


class CapRefused(RuntimeError):
    """The cap-raise mechanism refuses to act."""


class CapMissing(ValueError):
    """The frozen cap table has no entry for a stage or a configuration: the stage refuses."""


@dataclass(frozen=True)
class Rates:
    """What the rehearsal measures (seconds and bytes). ``update_seconds`` maps ``"<group>@L<layer>"`` (store-type groups, at each of the two read layers) or ``"<group>"`` (LoRA and E-table groups)
    to seconds per update; M-ii's is the rate at 64-row batches."""

    update_seconds: Mapping[str, float]
    calibrated_layer: int
    panel_seconds: float  # scoring E_A and E_B of one trained cell (CPU)
    replicate_extra_seconds: float  # combined panels, append point, ablations, GEN and router lane, diagnostic, retrieval (per replicate)
    fixed_seconds: float  # Stage 0, teacher scoring, general panel (once)
    timing_seconds: float  # the timing benchmark (once)
    gates2_seconds: float  # the second gates stage on registered seeds
    task_overhead_seconds: float  # per-process start-up: paid by every training task, every scoring task and every recomputation task
    train_peak_bytes: int = 0
    eval_peak_bytes: int = 0
    recompute_peak_bytes: int = 0
    task_peak_bytes: int = 0
    other_layer_seconds: float = 0.0  # the 200-update runs at the read layer calibration did not select (part of P)
    combined_cell_seconds: float = 0.0  # one arm-cell's combined scoring (C1, C2 and the single-task E_C answers) at the size of E_C: the combined-tasks addendum section 10
    combined_stage0_seconds: float = 0.0  # Stage 0 on the combined tasks, once per study
    analysis_seconds: float = 0.0  # the analysis stage on synthetic records of the whole registry (rehearsal), inside R
    report_seconds: float = 0.0  # the report stage on the same records, inside R
    train_device: str = "cpu"  # the device the rehearsal trained on: the freeze records it and registered training uses it (no silent fallback)
    train_device_reason: str = ""  # why the rehearsal trained on CPU, when it did

    def to_json(self) -> dict[str, Any]:
        d = asdict(self)
        d["update_seconds"] = dict(self.update_seconds)
        return d

    @staticmethod
    def from_json(d: Mapping[str, Any]) -> "Rates":
        return Rates(**{**d, "update_seconds": dict(d["update_seconds"])})


STORE_TYPE_GROUPS = ("ST1", "MAF", "MII", "MSEQ", "MJOINT", "MAGOLD", "ETABLE")  # E-table is one of the 16 store-type units (section 13.1): its rate is measured at each rehearsed read layer


def group_rate(group: str, rates: Rates, layer: int | None, slower: bool) -> float:
    """Seconds per update of a cell group. Store-type groups (E-table included) depend on the read layer; ``slower`` takes the slower of the rates at L = 4 and L = 12 (the rule for U = 1,000)."""
    if group in ("LORA1", "LSEQ", "LJOINT"):
        return float(rates.update_seconds[group])
    if slower:  # the slower of the rates measured at every read layer rehearsed (L = 4 and L = 12 in the registered rehearsal)
        measured = [float(v) for k, v in rates.update_seconds.items() if k.startswith(f"{group}@L")]
        if not measured:
            raise KeyError(f"no rate measured for {group}")
        return max(measured)
    ly = rates.calibrated_layer if layer is None else layer
    return float(rates.update_seconds[f"{group}@L{ly}"])


def reduced_updates(u: int) -> bool:
    """True for the reduced design (the smaller U of the registered rungs, 1,000), where the setting may be re-selected and the slower layer's rate applies."""
    return u == min(b for _a, b in rungs())


def cell_updates(group: str, u: int) -> int:
    """M-ii: U updates at 64-row batches (twice the cost per update, which the measured rate carries); M-joint and L-joint: 2U updates; every other cell U."""
    return 2 * u if group in ("MJOINT", "LJOINT") else u


def training_seconds(n: int, u: int, rates: Rates, *, slower: bool) -> float:
    """Training of the registered run: for each cell, updates x measured seconds per update, plus the task start-up of its process."""
    total = 0.0
    for cell in replicate_cells(0):
        total += cell_updates(cell.group, u) * group_rate(cell.group, rates, None, slower) + rates.task_overhead_seconds
    return n * total


def scoring_seconds(n: int, rates: Rates) -> float:
    """Every scoring of the registered run: per replicate 18 cell scorings (each its own process) and the extras; once, the fixed rows and the timing benchmark."""
    per_rep = 18 * (rates.panel_seconds + rates.task_overhead_seconds) + rates.replicate_extra_seconds + COMBINED_CELLS * rates.combined_cell_seconds
    return n * per_rep + rates.fixed_seconds + rates.combined_stage0_seconds + rates.timing_seconds


def recompute_seconds(n: int, rates: Rates) -> float:
    """The independent recomputation: one repetition of the scoring rows, the timing row included (the ADR's table figures 5.82-18.84 h include it; the lead's ruling of 2026-11-15)."""
    return scoring_seconds(n, rates)


def analysis_report_seconds(rates: Rates) -> float:
    """The rehearsed analysis and report time, each at least half the stated floor, always reserved inside R (so the headroom rule doubles it)."""
    return max(rates.analysis_seconds, CAP_FLOOR_SECONDS / 2) + max(rates.report_seconds, CAP_FLOOR_SECONDS / 2)


def registered_run_seconds(n: int, u: int, rates: Rates) -> dict[str, float]:
    """R(n, U) in seconds, with its parts. For U = 1,000 the training rates are the slower of the two read layers'."""
    slower = reduced_updates(u)
    parts = {
        "training": training_seconds(n, u, rates, slower=slower),
        "scoring": scoring_seconds(n, rates),
        "second_gates_stage": rates.gates2_seconds + rates.task_overhead_seconds,
        "recomputation": recompute_seconds(n, rates),
        "analysis_and_report": analysis_report_seconds(rates),
    }
    parts["total"] = sum(parts.values())
    return parts


def rungs() -> list[tuple[int, int]]:
    return [(int(a), int(b)) for a, b in B["rungs"]]


def config_key(n: int, u: int) -> str:
    return f"n{n}-U{u}"


@dataclass(frozen=True)
class RungDecision:
    outcome: str  # "rung 1".."rung 4" or NOT STARTED: BUDGET
    replicates: int | None
    updates: int | None
    charged_hours: float
    cap_hours: float
    projections: Mapping[str, float]  # config key -> R in hours
    reason: str = ""

    def to_json(self) -> dict[str, Any]:
        return {"outcome": self.outcome, "replicates": self.replicates, "updates": self.updates, "charged_hours": self.charged_hours, "cap_hours": self.cap_hours, "projections_hours": dict(self.projections), "reason": self.reason, "type": "analytical (a projection from measured rehearsal rates)"}


def rehearsal_rule(p_hours: float, rates: Rates, cap_hours: float) -> RungDecision:
    """The design is the first rung for which P + 2R <= cap; otherwise NOT STARTED: BUDGET. The memory rule is applied first: a rung whose peaks exceed the limits is not started."""
    proj = {config_key(n, u): registered_run_seconds(n, u, rates)["total"] / 3600.0 for n, u in rungs()}
    mem = memory_check(rates)
    if not mem["ok"]:
        return RungDecision(NOT_STARTED_BUDGET, None, None, p_hours, cap_hours, proj, "memory: " + "; ".join(mem["problems"]))
    for i, (n, u) in enumerate(rungs(), start=1):
        if p_hours + B["headroom"] * proj[config_key(n, u)] <= cap_hours:
            return RungDecision(f"rung {i}", n, u, p_hours, cap_hours, proj)
    return RungDecision(NOT_STARTED_BUDGET, None, None, p_hours, cap_hours, proj, "no rung satisfies P + 2R <= the cap")


# --- the cap extension ---------------------------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class CapRaise:
    old_cap_hours: float
    new_cap_hours: float
    charged_hours: float
    rung1_total_hours: float  # P + 2 R(4, 2000)
    ceiling_hit: bool
    projections_hours: Mapping[str, float]

    def to_json(self) -> dict[str, Any]:
        return {**asdict(self), "projections_hours": dict(self.projections_hours)}


def base_cap() -> float:
    return float(B["cap_hours"])


def ceiling() -> float:
    return float(B["cap_ceiling_hours"])


def propose_raise(p_hours: float, rates: Rates) -> CapRaise | None:
    """None if rung 1 fits the base cap. Otherwise the smallest whole number of hours at which rung 1 satisfies P + 2R <= cap, up to the ceiling (if rung 1 needs more, the cap is the ceiling and the
    rung rule applies against it)."""
    n, u = rungs()[0]
    r1 = registered_run_seconds(n, u, rates)["total"] / 3600.0
    need = p_hours + B["headroom"] * r1
    if need <= base_cap():
        return None
    whole = math.ceil(need - 1e-12)
    new = float(min(ceiling(), whole))
    proj = {config_key(a, b): registered_run_seconds(a, b, rates)["total"] / 3600.0 for a, b in rungs()}
    return CapRaise(base_cap(), new, p_hours, need, whole > ceiling(), proj)


def computed_cap(p_hours: float, rates: Rates) -> float:
    """The cap by the rule (the lead's ruling of 2026-11-15): 36 hours if rung 1 satisfies P + 2R <= 36; otherwise the smallest whole number of hours up to 72 at which rung 1 satisfies it; otherwise 72 (the
    rung order is then applied against 72, and NOT STARTED: BUDGET follows if no rung fits). Any other recorded cap is refused at the freeze."""
    proposal = propose_raise(p_hours, rates)
    return base_cap() if proposal is None else proposal.new_cap_hours


def plan_in_history(repo: Path | None) -> bool:
    """True if a freeze plan has ever been committed in the repository's history (any branch): a registered stage can have run after it, so the cap is never raised again."""
    if repo is None:
        return False
    r = subprocess.run(["git", "-C", str(repo), "log", "--all", "--format=%H", "-1", "--", str(core.PLAN_FILE)], capture_output=True, check=False)  # noqa: S603, S607
    return r.returncode == 0 and bool(r.stdout.strip())


def registered_seed_observed(ledger: Ledger | None, repo: Path | None = None) -> bool:
    """A registered replicate seed has been observed if the seed record holds a registered-run use, the study ledger holds a process marked registered, or a freeze plan is committed in the history. (The
    partition-side seeds 220901-220912 are drawn in the data-generation and partition steps before the rehearsal and are not replicate seeds; reading.)"""
    if any(u.mode == "registered-run" for u in core.seed_record()):
        return True
    if ledger is not None and ledger.registered_observed():
        return True
    return plan_in_history(repo)


def record_raise(rates: Rates, path: Path, ledger: Ledger, *, repo: Path | None = None, recorded_by: str = "lead") -> dict[str, Any]:
    """Record the raise, once, in the freeze folder and in the study ledger. The amount is recomputed here from the rehearsal record (``rates``) and P (the study ledger's total): the smallest whole
    number of hours, up to the ceiling, at which rung 1 satisfies P + 2R <= cap. Refused: after any registered seed has been observed (ledger, seed record, committed plan); a second raise; a raise when
    rung 1 already fits the base cap. Nothing is typed."""
    if registered_seed_observed(ledger, repo):
        raise CapRefused("refused: a registered seed has been observed; the cap is raised at the rehearsal's headroom check only, never after (section 13.3)")
    if path.exists() or ledger.cap_raise_entry() is not None:
        raise CapRefused("refused: the cap has been raised once already")
    proposal = propose_raise(ledger.total_hours(), rates)
    if proposal is None:
        raise CapRefused("refused: rung 1 fits the 36-hour cap; nothing to raise")
    rec = {"recorded_by": recorded_by, "recorded_at_stage": "rehearsal headroom check", **proposal.to_json(), "rule": "ADR-0022 section 13.3 cap extension; ceiling 72 h; once; before any registered seed is observed; recomputed from the rehearsal record"}
    ledger.append_cap_raise(proposal.new_cap_hours, {"charged_hours": proposal.charged_hours, "rung1_total_hours": proposal.rung1_total_hours})
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(path, (json.dumps(core.jsonable(rec), sort_keys=True, indent=1) + "\n").encode())
    return rec


def effective_cap(path: Path) -> float:
    """36 hours unless a raise is recorded in the file."""
    if not path.exists():
        return base_cap()
    new = float(json.loads(path.read_text())["new_cap_hours"])
    if new > ceiling():
        raise CapRefused("the recorded cap is above the ceiling")
    return new


def verify_raise(path: Path, p_hours: float, rates: Rates, ledger: Ledger) -> float:
    """The cap in force at the freeze: the raise file and the ledger's raise entry must agree, and the recorded cap must equal the cap computed now from P and the rates (``computed_cap``); returns the cap.
    Refuses on any difference (a raise that was typed, edited, deleted or made twice, or a raise declined where the rule requires it)."""
    in_file = effective_cap(path)
    in_ledger = ledger.cap_hours()
    if in_file != in_ledger:
        raise CapRefused(f"refused: the raise file ({in_file} h) and the study ledger ({in_ledger} h) disagree")
    computed = computed_cap(p_hours, rates)
    if in_file != computed:  # the cap is a computed rule: a base cap where a raise is required, a raise that is not the computed amount, or any other number is refused
        raise CapRefused(f"refused: the recorded cap {in_file} h differs from the cap computed by the rule from the rehearsal record and P ({computed} h)")
    return in_file


def headroom_check(p_hours: float, rates: Rates, ledger: Ledger | None, raise_path: Path) -> dict[str, Any]:
    """The rehearsal's headroom check: the proposal (if rung 1 does not fit 36 h), the cap in force (recorded raise or 36) and the rung rule's decision against it. The proposal takes effect only through
    ``record_raise``."""
    proposal = propose_raise(p_hours, rates)
    cap = ledger.cap_hours() if ledger is not None else effective_cap(raise_path)
    decision = rehearsal_rule(p_hours, rates, cap)
    return {"proposal": None if proposal is None else proposal.to_json(), "cap_in_force_hours": cap, "decision": decision.to_json()}


# --- memory (8 GiB per worker, 24 GiB aggregate) --------------------------------------------------------------------------------------------------
def memory_check(rates: Rates, workers: int | None = None) -> dict[str, Any]:
    """Twice the largest of the training, evaluation, recomputation and whole-task peaks (audit M2: the training peak alone is not enough) must fit 8 GiB per worker, and workers x twice that peak 24 GiB in aggregate.
    The ADR names no worker count; the projection is serial and ``workers`` defaults to the config value (PENDING LEAD REVIEW)."""
    k = int(B["workers"]) if workers is None else workers
    per = float(B["memory_per_worker_gib"]) * GIB
    agg = float(B["memory_aggregate_gib"]) * GIB
    peaks = {"training": rates.train_peak_bytes, "evaluation": rates.eval_peak_bytes, "recomputation": rates.recompute_peak_bytes, "task": rates.task_peak_bytes}
    worst = max(peaks.values())
    h = float(B["headroom"])  # the rehearsal must show twice the measured peak within the limits (the lead's ruling of 2026-11-15)
    problems = [f"{name} peak {v / GIB:.2f} GiB: twice that exceeds {B['memory_per_worker_gib']} GiB per worker" for name, v in peaks.items() if h * v > per]
    if k * h * worst > agg:
        problems.append(f"{k} workers x twice {worst / GIB:.2f} GiB exceed {B['memory_aggregate_gib']} GiB in aggregate")
    return {"ok": not problems, "problems": problems, "peaks_bytes": peaks, "workers": k}


# --- stage caps per configuration (frozen) -------------------------------------------------------------------------------------------------------
REGISTERED_STAGES = ("gates", "train", "evaluate", "timing", "recompute", "analysis", "report")


def stage_seconds(n: int, u: int, rates: Rates) -> dict[str, float]:
    """The projected seconds of each registered stage at a configuration, task start-up included."""
    slower = reduced_updates(u)
    per_rep_eval = 18 * (rates.panel_seconds + rates.task_overhead_seconds) + rates.replicate_extra_seconds + COMBINED_CELLS * rates.combined_cell_seconds
    return {
        "gates": rates.gates2_seconds + rates.task_overhead_seconds,
        "train": training_seconds(n, u, rates, slower=slower),
        "evaluate": n * per_rep_eval + rates.fixed_seconds + rates.combined_stage0_seconds,
        "timing": rates.timing_seconds + rates.task_overhead_seconds,
        "recompute": recompute_seconds(n, rates),
        "analysis": max(rates.analysis_seconds, CAP_FLOOR_SECONDS / 2),
        "report": max(rates.report_seconds, CAP_FLOOR_SECONDS / 2),
    }


def stage_caps(rates: Rates) -> dict[str, dict[str, float]]:
    """One entry per design configuration and stage: each cap is the headroom (2x) times the projected seconds of that stage, with the floor for analysis and report. A stage whose configuration has no
    entry refuses (``cap_for``)."""
    out: dict[str, dict[str, float]] = {}
    for n, u in rungs():
        sec = stage_seconds(n, u, rates)
        out[config_key(n, u)] = {k: max(B["headroom"] * v, CAP_FLOOR_SECONDS) if k in ("analysis", "report") else B["headroom"] * v for k, v in sec.items()}
    return out


def cap_for(table: Mapping[str, Mapping[str, float]], stage: str, n: int, u: int) -> float:
    key = config_key(n, u)
    if key not in table or stage not in table[key]:
        raise CapMissing(f"the frozen cap table has no entry for stage {stage!r} at configuration {key}")
    return float(table[key][stage])


def projection_record(p_hours: float, rates: Rates, decision: RungDecision) -> dict[str, Any]:
    return {"rates": rates.to_json(), "charged_hours_at_rehearsal_end": p_hours, "decision": decision.to_json(), "parts_seconds": {config_key(n, u): registered_run_seconds(n, u, rates) for n, u in rungs()}, "type": "analytical (a projection from measured rehearsal rates)"}


def charged_after_each(stages: Sequence[tuple[str, float]]) -> list[tuple[str, float]]:
    """Running total of charged hours for a sequence of (stage, hours); used by the ledger tests."""
    acc, out = 0.0, []
    for name, h in stages:
        acc += h
        out.append((name, acc))
    return out

