# ruff: noqa: E501
"""P10S1 frozen inputs of the analysis (ADR-0021 sections 5.4, 10.2, 10.3): the two cost measures per update (measured CPU seconds from the isolated timing part of the rehearsal,
analytic multiply-adds), the matched-compute (MC) plan (every pair of cells compared under MC, its multiplier, the cheaper cell's snapshot or MC-SHORT) and the snapshots each
cell therefore needs. All pure functions of the plan and the cost tables; the freeze procedure writes their result into ``plan.json`` and the analysis reads it back.

Analytic multiply-adds per update (the lead's ruling, ADR-0021 section 22 M6): one whole training update including the frozen backbone's forward and backward; the formula is in the
config (``core.MADDS_FORMULA``).
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from . import classes as C
from . import core

ANALYTIC_OPTIMIZER_MADDS = 4
FOQ_FAMILY = ("F-OQ", "T-OQ", "H8")


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


BATCH_CONTEXTS = core.BATCH_CONTEXTS
POSITIONS = core.INPUT_LENGTH
WIDTH_, FFN_, VOCAB_ = 32, 64, 256


def backbone_madds(batch: int = BATCH_CONTEXTS, t: int = POSITIONS) -> dict[str, int]:
    """The frozen backbone's multiply-adds in one training update (``core.MADDS_FORMULA``): forward over both blocks and the output head; backward through block 1 and the head only (no weight
    gradients: the weights are frozen), with the two attention products' operands both needing gradients."""
    attn = 4 * t * t * 8  # one attention product over 4 heads of width 8
    block_forward = t * WIDTH_ * 96 + attn + attn + t * WIDTH_ * WIDTH_ + 2 * t * WIDTH_ * FFN_
    forward = batch * (2 * block_forward + t * WIDTH_ * VOCAB_)
    backward = batch * (t * WIDTH_ * 96 + t * WIDTH_ * WIDTH_ + 2 * t * WIDTH_ * FFN_ + 4 * attn + t * WIDTH_ * VOCAB_)
    return {"forward": forward, "backward": backward, "total": forward + backward}


def memory_madds(arm: str, slots: int, batch: int = BATCH_CONTEXTS) -> int:
    """The arm's matrix-product multiply-adds in one update (queries Q = 8 x batch): scoring forward and its gradient wrt the keys, the output projection forward and both gradients."""
    q = core.ANSWER_SITES_PER_CONTEXT * batch
    kw, w = core.KEY_WIDTH, core.HIDDEN_WIDTH
    wo = 3 * q * w * w
    if arm == "F-OQ":
        return 2 * q * slots * kw + wo
    if arm == "T-OQ":
        return 2 * q * ((slots // core.BRANCH_SIZE) * kw + core.TREE_CANDIDATES * kw) + wo
    if arm in ("H8", "R2"):
        return wo
    if arm == "D-OQ":
        h = core.doq_hidden(slots)
        return 2 * q * kw * h + 3 * q * h * w
    raise ValueError(f"unknown arm {arm!r}")


def matmul_madds_per_update(arm: str, slots: int, batch: int = BATCH_CONTEXTS) -> int:
    """Backbone plus arm matrix products: what torch's FLOP counter sees (divided by two); a test compares them at tiny size."""
    return backbone_madds(batch)["total"] + memory_madds(arm, slots, batch)


def gather_madds(arm: str, slots: int, batch: int = BATCH_CONTEXTS) -> int:
    """The gather-weighted sum of the value read, ``(weights[..., None] * table[chosen]).sum(-2)``, which torch's FLOP counter does not see (ADR-0021 section 22.1): per query and value
    width, 3 x 8 reads for F-OQ and T-OQ (forward and both gradients), 2 x 8 for H8, 2 x 1 for R2, none for D-OQ."""
    q = core.ANSWER_SITES_PER_CONTEXT * batch
    reads = {"F-OQ": 3 * 8, "T-OQ": 3 * 8, "H8": 2 * 8, "R2": 2 * 1, "D-OQ": 0}
    if arm not in reads:
        raise ValueError(f"unknown arm {arm!r}")
    return q * reads[arm] * core.HIDDEN_WIDTH


def analytic_madds_per_update(arm: str, slots: int) -> float:
    """The whole-update multiply-add count of section 5.4 as the lead ruled it (ADR-0021 section 22, M6): the frozen backbone's forward and backward every arm pays, the arm's matrix
    products, the gather-weighted sum of the value read (``gather_madds``), and 4 x trainable parameters for AdamW. Written out in the config (``core.MADDS_FORMULA``)."""
    if slots == core.SATURATION_ONLY_CELL[1] and arm != "F-OQ":
        raise ValueError(f"{arm} is not defined at 256 slots: the saturation cell is F-OQ's alone (ADR-0021 section 5.1)")
    return float(matmul_madds_per_update(arm, slots) + gather_madds(arm, slots) + ANALYTIC_OPTIMIZER_MADDS * trainable_parameters(arm, slots))


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
    claim: str = "large"  # the cell whose advantage would be claimed (section 5.4): the larger cell on the capacity line, the memory arm (role small) in the dense labels


def mc_pairs(plan: core.Plan) -> list[McPair]:
    """Every pair of cells compared under MC: the four steps of F-OQ, T-OQ and H8 (small and large slots of one row; claim: the larger cell), and the memory-arm cell against D-OQ at the larger
    cell of every step with a D-OQ cell (role small: the arm, role large: D-OQ; claim: the arm)."""
    out: list[McPair] = []
    dense_cells = set(core.arm_cells(plan, "D-OQ"))
    for arm in FOQ_FAMILY:
        for step in plan.steps:
            u_p = core.u_p_of(plan, step.facts)
            out.append(McPair(f"cap|{arm}|{step.name}", arm, (arm, step.facts, step.small), (arm, step.facts, step.large), u_p, "large"))
            if (step.facts, step.large) in dense_cells:
                out.append(McPair(f"dense|{arm}|{core.cell_name(step.facts, step.large)}", arm, (arm, step.facts, step.large), ("D-OQ", step.facts, step.large), u_p, "small"))
    return out


def run_of(plan: core.Plan, cell: tuple[str, int, int]) -> int:
    return core.run_updates_of(plan, cell[0], cell[1], cell[2])


def build_mc(plan: core.Plan, cost: dict[str, dict[str, dict[str, float]]]) -> dict[str, C.McEntry]:
    """The MC entry of every pair (``classes.mc_pair``): costlier cell at U_P, cheaper at the smallest grid snapshot whose cumulative cost is at least that; MC-SHORT when the snapshot exceeds the
    other cell's run length; where the measures disagree the pair is read in the comparator's favour (MC-AMBIGUOUS annotation)."""
    out: dict[str, C.McEntry] = {}
    for p in mc_pairs(plan):
        a, b = p.small, p.large
        out[p.key] = C.mc_pair(costs_of(cost, a[0], a[2]), costs_of(cost, b[0], b[2]), p.u_p, run_of(plan, a), run_of(plan, b), p.claim)
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
    return core.cell_snapshot_updates(cell, plan.unit, extra)


def mc_to_json(mc: dict[str, C.McEntry]) -> dict[str, Any]:
    return {k: {"status": e.status, "small_update": e.small_update, "large_update": e.large_update, "multiplier": e.multiplier, "cheaper": e.cheaper, "annotation": e.annotation} for k, e in sorted(mc.items())}


def mc_from_json(data: dict[str, Any]) -> dict[str, C.McEntry]:
    return {k: C.McEntry(v["status"], v["small_update"], v["large_update"], float(v["multiplier"]), v["cheaper"], v.get("annotation")) for k, v in data.items()}


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
    dense_rates: dict[str, float] = field(default_factory=dict)  # D-OQ unit (core.dense_unit_of) -> calibrated learning rate
    h8_undertrained: list[str] = field(default_factory=list)
    h8_calibrated: list[str] = field(default_factory=lambda: [core.cell_name(f, n) for f, n in core.H8_REPORT_CELLS])  # the cells whose H8 calibration has all four views (audit m7)
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
            "h8_undertrained": list(self.h8_undertrained), "h8_calibrated": list(self.h8_calibrated), "s0_status": self.s0_status, "lane_status": self.lane_status, "no_loaded_transitions": list(self.no_loaded_transitions), "cuts": list(self.cuts),
        }  # fmt: skip

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "Frozen":
        return cls(
            plan=core.Plan.from_json(data["plan"]), cost=data["cost"], mc=mc_from_json(data["mc"]), dense_rates={str(k): float(v) for k, v in data["dense_rates"].items()},
            h8_undertrained=list(data["h8_undertrained"]), h8_calibrated=list(data.get("h8_calibrated", [core.cell_name(f, n) for f, n in core.H8_REPORT_CELLS])), s0_status=data["s0_status"], lane_status=data["lane_status"], no_loaded_transitions=list(data["no_loaded_transitions"]), cuts=list(data.get("cuts", [])),
        )  # fmt: skip

    @classmethod
    def build(cls, plan: core.Plan, cpu_per_update: dict[tuple[str, int], float], **kw: Any) -> "Frozen":
        cost = cost_table(cpu_per_update)
        return cls(plan=plan, cost=cost, mc=build_mc(plan, cost), **kw)


def default_cpu_table() -> dict[tuple[str, int], float]:
    """A deterministic placeholder cost table (seconds per update; synthetic records and unit tests only, never a measurement): cost grows with the work per query."""
    out: dict[tuple[str, int], float] = {}
    for arm, slot_counts in core.arm_slot_counts().items():
        for n in slot_counts:
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


# S0's registered outcome labels (ADR-0020 section 8.7's outcome table: rows 1 to 6; the NOT STARTED row's label is "NOT STARTED — NO P9-II CALIBRATION RECORD"; ENGINEERING_FAIL and INCOMPLETE are
# row 2's two labels). An --s0-record whose outcome is none of these is refused, never read as "no interface qualified".
S0_OUTCOMES = (
    LANE_QUALIFIED_BOTH, LANE_QUALIFIED_4096, "ADDRESSING-NOT-QUALIFIED", "INCONCLUSIVE", "ENGINEERING_FAIL", "INCOMPLETE", "NOT STARTED", "NOT STARTED — NO P9-II CALIBRATION RECORD",
)  # fmt: skip
OMITTED_LANE_LABELS = ("OMITTED — QUALIFIED AT 4,096 ONLY", "OMITTED — SUPERVISED ARM HAS NO 8K/4K CELL", "OMITTED — NOT OVERLOAD-QUALIFIED", LANE_OMITTED_NO_INTERFACE)
RULING_KEYS = ("ruled_by", "date", "adr_section", "s0_outcome", "s0_candidate", "s0_overload_qualified", "lane_status", "s0_commit", "s0_record_sha256")


def validate_s0_record(record: Mapping[str, Any]) -> None:
    """Refuse (``ValueError``) an S0 record whose outcome is not one of S0's registered outcome labels."""
    outcome = record.get("outcome")
    if outcome not in S0_OUTCOMES:
        raise ValueError(f"S0 record outcome {outcome!r} is not one of S0's registered outcome labels {list(S0_OUTCOMES)}")


def check_lane_ruling(ruling: Mapping[str, Any], record: Mapping[str, Any], lane: str) -> None:
    """The lead's lane ruling (ADR-0021 section 25.17 point 4) against S0's record and the label the code derives from it (``ValueError`` when any holds): the ruling states every field; its S0 outcome,
    candidate and overload flag equal the record's; the label the code derives equals the ruling's; and that label is one of the OMITTED labels (the 'would run' label is never accepted: the lane
    cannot run in this tree)."""
    missing = [k for k in RULING_KEYS if k not in ruling]
    if missing:
        raise ValueError(f"the lane ruling lacks {missing}")
    hashes = ruling["s0_record_sha256"]
    if not isinstance(hashes, dict) or len(hashes) < 1 or not all(isinstance(v, str) and len(v) == 64 for v in hashes.values()):
        raise ValueError("the lane ruling's s0_record_sha256 must map S0's record paths to sha256 digests")
    if (ruling["s0_outcome"], ruling["s0_candidate"], bool(ruling["s0_overload_qualified"])) != (record.get("outcome"), record.get("candidate"), bool(record.get("overload_qualified"))):
        raise ValueError("the lane ruling's S0 outcome, candidate or overload flag differs from S0's record")
    if lane not in OMITTED_LANE_LABELS:
        raise ValueError(f"the label derived from S0's record is {lane!r}, not an OMITTED label: the lane cannot run in this tree and no ruling covers it")
    if lane != ruling["lane_status"]:
        raise ValueError(f"the label derived from S0's record ({lane!r}) differs from the ruled label ({ruling['lane_status']!r})")


def s0_status_and_lane(record: Mapping[str, Any] | None) -> tuple[str, str, bool]:
    """From S0's recorded outcome at the freeze (``{"outcome": ..., "candidate": ..., "overload_qualified": bool}``; None when S0 has no outcome): S0's status line (K7(c)), lane L's status, and
    whether the question returns to the lead (ADR-0021 section 22 (b) and the lead's ruling P1: S0 qualified ANY interface before the freeze, whether or not the lane would run; nothing is printed OMITTED in that case)."""
    if record is None:
        return S0_NOT_DECIDED, LANE_OMITTED_NO_INTERFACE, False
    validate_s0_record(record)
    outcome = record.get("outcome")
    status = f"S0 {outcome}" if outcome else S0_NOT_DECIDED
    lane = lane_l_status(outcome, record.get("candidate"), bool(record.get("overload_qualified")))
    return status, lane, outcome in (LANE_QUALIFIED_BOTH, LANE_QUALIFIED_4096)  # any qualified interface before the freeze returns to the lead, whether or not the lane would run (lead's ruling P1)
