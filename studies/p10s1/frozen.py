# ruff: noqa: E501
"""P10S1 frozen inputs of the analysis (ADR-0021 sections 5.4, 10.2, 10.3): the two cost measures per update (measured CPU seconds from the isolated timing part of the rehearsal,
analytic multiply-adds), the matched-compute (MC) plan (every pair of cells compared under MC, its multiplier, the cheaper cell's snapshot or MC-SHORT) and the snapshots each
cell therefore needs. All pure functions of the plan and the cost tables; the freeze procedure writes their result into ``plan.json`` and the analysis reads it back.

Analytic multiply-adds per update (READING: the ADR names the measure without a formula): 3 x 128 x W (forward and backward over the batch's 128 queries, W of section 7.4) plus
4 x trainable parameters (AdamW updates every parameter every step). W is the counted work per query of ``core.work_formula``.
"""

from dataclasses import dataclass, field
from typing import Any

from . import classes as C
from . import core

ANALYTIC_OPTIMIZER_MADDS = 4
FOQ_FAMILY = ("F-OQ", "T-OQ", "H8")
STUDY_B_ARMS = ("F-OQ", "T-OQ")  # F-OQ-IVF's cells are F-OQ's cells


def trainable_parameters(arm: str, slots: int) -> int:
    """Trainable parameters of a cell (the numbers ``model.parameter_report`` returns)."""
    kw, w = core.KEY_WIDTH, core.HIDDEN_WIDTH
    gate_wo = w * w + 1
    if arm == "F-OQ":
        return slots * (kw + w) + gate_wo
    if arm == "T-OQ":
        return slots * (kw + w) + (slots // core.BRANCH_SIZE) * kw + gate_wo
    if arm in ("H8", "R2"):
        return slots * w + gate_wo
    if arm == "D-OQ":
        return core.doq_trainable_parameters(core.doq_hidden(slots))
    raise ValueError(f"unknown arm {arm!r}")


def analytic_madds_per_update(arm: str, slots: int) -> float:
    """3 x 128 x W + 4 x trainable parameters (see the module docstring)."""
    w = core.work_formula(arm, slots)["W"]
    return float(3 * core.ANSWER_SITES_PER_BATCH * w + ANALYTIC_OPTIMIZER_MADDS * trainable_parameters(arm, slots))


def cost_table(cpu_per_update: dict[tuple[str, int], float]) -> dict[str, dict[str, dict[str, float]]]:
    """``cost[arm][slots] = {"cpu": seconds per update (measured), "madds": analytic}`` for every arm and slot count of ``cpu_per_update``."""
    out: dict[str, dict[str, dict[str, float]]] = {}
    for (arm, slots), cpu in sorted(cpu_per_update.items()):
        out.setdefault(arm, {})[str(slots)] = {"cpu": float(cpu), "madds": analytic_madds_per_update(arm, slots)}
    return out


def costs_of(cost: dict[str, dict[str, dict[str, float]]], arm: str, slots: int) -> dict[str, float]:
    return cost["F-OQ" if arm == "F-OQ-IVF" else arm][str(slots)]


# --- the MC plan --------------------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class McPair:
    key: str
    arm: str
    small: tuple[str, int, int]  # (arm, facts, slots) of the role "small"
    large: tuple[str, int, int]
    u_p: int


def mc_pairs(plan: core.Plan) -> list[McPair]:
    """Every pair of cells compared under MC: the capacity steps of F-OQ, T-OQ and H8 (small and large slots of one row), the memory-arm cell against D-OQ at the larger cell of
    every step with a D-OQ cell (role small: the arm, role large: D-OQ), and the two diagonal steps of F-OQ and T-OQ."""
    out: list[McPair] = []
    dense_cells = set(core.arm_cells(plan, "D-OQ"))
    for arm in FOQ_FAMILY:
        for step in plan.steps:
            u_p = core.u_p_of(plan, step.facts)
            out.append(McPair(f"cap|{arm}|{step.name}", arm, (arm, step.facts, step.small), (arm, step.facts, step.large), u_p))
            if (step.facts, step.large) in dense_cells:
                out.append(McPair(f"dense|{arm}|{core.cell_name(step.facts, step.large)}", arm, (arm, step.facts, step.large), ("D-OQ", step.facts, step.large), u_p))
    for arm in STUDY_B_ARMS:
        for k, ((f0, n0), (f1, n1)) in enumerate((((2048, 4096), (8192, 16384)), ((8192, 16384), (32768, 65536)))):
            out.append(McPair(f"diag|{arm}|{k}", arm, (arm, f0, n0), (arm, f1, n1), plan.unit))
    return out


def build_mc(plan: core.Plan, cost: dict[str, dict[str, dict[str, float]]]) -> dict[str, C.McEntry]:
    """The MC entry of every pair (``classes.mc_pair``): costlier cell at U_P, cheaper at the smallest grid snapshot whose cumulative cost is at least that; MC-SHORT when the
    snapshot exceeds the cheaper cell's run length."""
    out: dict[str, C.McEntry] = {}
    for p in mc_pairs(plan):
        a, b = p.small, p.large
        out[p.key] = C.mc_pair(costs_of(cost, a[0], a[2]), costs_of(cost, b[0], b[2]), p.u_p, core.run_length(a[0], a[2], p.u_p), core.run_length(b[0], b[2], p.u_p))
    return out


def required_snapshots(plan: core.Plan, mc: dict[str, C.McEntry]) -> dict[tuple[str, int, int], set[int]]:
    """The matched-compute snapshots each cell must have: ``(arm, facts, slots)`` -> updates (section 5.4: 'and every matched-compute snapshot')."""
    need: dict[tuple[str, int, int], set[int]] = {}
    for p in mc_pairs(plan):
        e = mc.get(p.key)
        if e is None or not e.ok():
            continue
        need.setdefault(p.small, set()).add(int(e.small_update))  # type: ignore[arg-type]
        need.setdefault(p.large, set()).add(int(e.large_update))  # type: ignore[arg-type]
    return need


def snapshots_for(cell: core.Cell, plan: core.Plan, mc: dict[str, C.McEntry]) -> tuple[int, ...]:
    """The snapshots of a registered cell: the grid of section 5.4 plus its matched-compute snapshots. F-OQ's snapshots serve F-OQ-IVF (same training)."""
    extra = required_snapshots(plan, mc).get((cell.arm, cell.facts, cell.slots), set())
    return core.snapshot_updates(cell.u_p, cell.run_updates, extra)


def mc_to_json(mc: dict[str, C.McEntry]) -> dict[str, Any]:
    return {k: {"status": e.status, "small_update": e.small_update, "large_update": e.large_update, "multiplier": e.multiplier, "cheaper": e.cheaper} for k, e in sorted(mc.items())}


def mc_from_json(data: dict[str, Any]) -> dict[str, C.McEntry]:
    return {k: C.McEntry(v["status"], v["small_update"], v["large_update"], float(v["multiplier"]), v["cheaper"]) for k, v in data.items()}


# --- everything the analysis reads from the freeze -----------------------------------------------------------------------------------------
S0_NOT_DECIDED = "S0 NOT YET DECIDED"
LANE_OMITTED_NO_INTERFACE = "OMITTED — no interface qualified before the freeze"


@dataclass
class Frozen:
    """What the freeze fixes and the analysis needs: the plan (rows, seed block, cuts, lane L), the two cost tables, the MC plan, D-OQ's rates, H8's UNDERTRAINED cells, S0's status
    line (K7(c)), the lane L status and the directed no-loaded-row transitions."""

    plan: core.Plan = field(default_factory=core.Plan)
    cost: dict[str, dict[str, dict[str, float]]] = field(default_factory=dict)
    mc: dict[str, C.McEntry] = field(default_factory=dict)
    dense_rates: dict[int, float] = field(default_factory=dict)
    h8_undertrained: list[str] = field(default_factory=list)
    s0_status: str = S0_NOT_DECIDED
    lane_status: str = LANE_OMITTED_NO_INTERFACE
    no_loaded_transitions: list[str] = field(default_factory=list)
    cuts: list[str] = field(default_factory=list)

    def entry(self, key: str) -> C.McEntry:
        """The MC entry of ``key``; a pair the freeze did not record is not established."""
        return self.mc.get(key, C.McEntry(C.MC_SHORT, None, None, float("nan"), None))

    def snapshots(self, cell: core.Cell) -> tuple[int, ...]:
        return snapshots_for(cell, self.plan, self.mc)

    def as_json(self) -> dict[str, Any]:
        return {
            "plan": self.plan.as_json(), "cost": self.cost, "mc": mc_to_json(self.mc), "dense_rates": {str(k): v for k, v in sorted(self.dense_rates.items())},
            "h8_undertrained": list(self.h8_undertrained), "s0_status": self.s0_status, "lane_status": self.lane_status, "no_loaded_transitions": list(self.no_loaded_transitions), "cuts": list(self.cuts),
        }  # fmt: skip

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "Frozen":
        return cls(
            plan=core.Plan.from_json(data["plan"]), cost=data["cost"], mc=mc_from_json(data["mc"]), dense_rates={int(k): float(v) for k, v in data["dense_rates"].items()},
            h8_undertrained=list(data["h8_undertrained"]), s0_status=data["s0_status"], lane_status=data["lane_status"], no_loaded_transitions=list(data["no_loaded_transitions"]), cuts=list(data.get("cuts", [])),
        )  # fmt: skip

    @classmethod
    def build(cls, plan: core.Plan, cpu_per_update: dict[tuple[str, int], float], **kw: Any) -> "Frozen":
        cost = cost_table(cpu_per_update)
        return cls(plan=plan, cost=cost, mc=build_mc(plan, cost), **kw)


def default_cpu_table() -> dict[tuple[str, int], float]:
    """A deterministic placeholder cost table (seconds per update; synthetic records and unit tests only, never a measurement): cost grows with the work per query."""
    out: dict[tuple[str, int], float] = {}
    for arm in (*core.ARMS,):
        for n in core.SLOT_COUNTS:
            w = core.work_formula(arm, n)["W"]
            out[(arm, n)] = 1e-3 + 1e-7 * w
    return out


LANE_QUALIFIED_BOTH = "ADDRESSING-QUALIFIED (4,096 AND 16,384)"
LANE_QUALIFIED_4096 = "ADDRESSING-QUALIFIED AT 4,096 ONLY"
LANE_WOULD_RUN = "WOULD RUN — NOT IMPLEMENTED (F-LA is S0's frozen candidate; its code is not in this tree)"


def lane_l_status(s0_outcome: str | None, candidate: str | None = None, overload_qualified: bool = False) -> str:
    """Lane L's status at the freeze (section 5.6 items 1 to 3). The lane exists only if, before the freeze, S0 has the outcome ADDRESSING-QUALIFIED (4,096 AND 16,384) with Q1 recomputed by
    the auditor. Otherwise it prints one of the four OMITTED labels: QUALIFIED AT 4,096 ONLY; SUPERVISED ARM HAS NO 8K/4K CELL (the candidate is A1 or A2); NOT OVERLOAD-QUALIFIED; or
    no interface qualified before the freeze (ADDRESSING-NOT-QUALIFIED, INCONCLUSIVE, ENGINEERING_FAIL, INCOMPLETE, NOT STARTED, or nothing recorded). A qualification recorded after
    the freeze changes nothing. Even when the lane would run, this tree cannot run it: F-LA is S0's frozen candidate and S0's code is not here (the freeze refuses ``--lane-l``)."""
    if s0_outcome == LANE_QUALIFIED_4096:
        return "OMITTED — QUALIFIED AT 4,096 ONLY"
    if s0_outcome == LANE_QUALIFIED_BOTH:
        if candidate in ("A1", "A2"):
            return "OMITTED — SUPERVISED ARM HAS NO 8K/4K CELL"
        if not overload_qualified:
            return "OMITTED — NOT OVERLOAD-QUALIFIED"
        return LANE_WOULD_RUN
    return LANE_OMITTED_NO_INTERFACE
