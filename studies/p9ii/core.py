# ruff: noqa: E501
"""P9II shared contract: constants of ADR-0019 revision 4, the cell registry (calibration 22, Stage 1 128,
Stage 2 16 to 40, Stage 3 6 or 8), seeds and their disjointness, the schedules in exposures per fact, the
calibration selection rule, config, identity hashes, record IO, run manifests with the environment, and the
two charged-time ledgers (Budget A and Budget B).

Specification: ``docs/decisions/ADR-0019-robust-sparse-address-learning.md`` (revision 4). Every number
below is copied from the ADR with its section. Nothing here trains or evaluates a model.

Status: implementation self-checked only. Not independent review, not Astra validation, not human approval.
"""

import hashlib
import json
import math
import os
import platform
import re
import sys
import tomllib
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path
from typing import Any, NamedTuple

import torch

from arborlm.config import _validate
from arborlm.io import canonical_json, file_sha256, read_json, sha256, write_json
from studies.p9 import core as p9core
from studies.p9i import core as p9icore

# --- identity of the study -----------------------------------------------------------------------------------
SPEC = "docs/decisions/ADR-0019-robust-sparse-address-learning.md"
STUDY = "P9II"
FAMILY = "P9II_ROBUST_SPARSE_ADDRESS_LEARNING"
SCHEMA = 1
DEFAULT_CONFIG = Path("configs/p9ii_addressing.toml")
LAUNCH_DIR = Path("studies/p9ii/launch")

# Modules of other studies whose code this study imports and runs; hashed into the source digest (a test
# scans the p9ii sources and fails when a studies.p9 or studies.p9i module is imported that is not listed).
IMPORTED_P9_MODULES = ("__init__", "controls", "core", "data", "evaluate", "model", "objective", "pool", "train")
IMPORTED_P9I_MODULES = ("__init__", "classes", "core", "evaluate", "model", "report", "stages", "train")

# --- the task and the memory (ADR-0019 section 3; imported from P9 / P9-I so there is one namespace) -----------
ALPHABET = p9core.ALPHABET
ALPHABET_SIZE = p9core.ALPHABET_SIZE
ALPHABET_BASE = ALPHABET[0]
CONTEXT_BYTES, INPUT_LENGTH = p9core.CONTEXT_BYTES, p9core.INPUT_LENGTH
RECORD_BYTES, RECORDS_PER_CONTEXT = p9core.RECORD_BYTES, p9core.RECORDS_PER_CONTEXT
ANSWER_SITES_PER_CONTEXT = p9core.ANSWER_SITES_PER_CONTEXT
ANSWER_SITE_POSITIONS = p9core.ANSWER_SITE_POSITIONS
BATCH_CONTEXTS = p9core.BATCH_CONTEXTS  # 16 contexts = 128 answer sites
ANSWER_SITES_PER_BATCH = p9core.ANSWER_SITES_PER_BATCH
SLOTS_BY_SIZE = p9core.SLOTS_BY_SIZE  # 4,096 / 16,384 / 65,536
FACTS_PROPORTIONAL = p9core.FACTS_PROPORTIONAL  # 2,048 / 8,192 / 32,768
KEY_WIDTH, TOP, TEMPERATURE = p9core.KEY_WIDTH, p9core.TOP, p9core.TEMPERATURE
HIDDEN_WIDTH = p9core.HIDDEN_WIDTH
WINDOW = p9icore.WINDOW  # 7
LEARNING_RATE, CLIP_NORM = p9core.LEARNING_RATE, p9core.CLIP_NORM
CHANCE = p9core.CHANCE

# --- arms (section 4) ---------------------------------------------------------------------------------------------
LEARNED_ARMS = ("A0", "A1", "A2", "A4", "A5-C", "A5-D", "A1-S")
REFERENCE_ARMS = ("A6", "A7")
ARMS = (*LEARNED_ARMS, *REFERENCE_ARMS)
LABEL_FREE_ARMS = ("A0", "A4", "A5-C", "A5-D")  # no fact identity in training
SUPERVISED_ARMS = ("A1", "A2")  # address-supervised in training
TARGET_ARMS = ("A1", "A2", "A1-S")  # arms with a target slot (A1-S: a random one)
CONSTANT_OBJECTIVE_ARMS = ("A0", "A1", "A1-S", "A5-C", "A5-D", "A6", "A7")
SCHEDULED_ARMS = ("A2", "A4")
BASE_ARM = {"A0": "W7", "A1": "W7", "A2": "W7", "A4": "W7", "A5-C": "W7", "A5-D": "W7", "A1-S": "W7", "A6": "R1", "A7": "D7"}
ADVANCE_ORDER = ("A5-C", "A5-D", "A4", "A2", "A1")  # section 8.4 Stage 1 gate
CARRY_FORWARD_ORDER = ("A0", "A5-C", "A5-D", "A4", "A2", "A1")  # section 8.6
SUPERVISION_LABEL = {"A0": "(LABEL-FREE)", "A4": "(LABEL-FREE)", "A5-C": "(LABEL-FREE)", "A5-D": "(LABEL-FREE)", "A1": "(ADDRESS-SUPERVISED IN TRAINING)", "A2": "(ADDRESS-SUPERVISED IN TRAINING)"}
MAX_ADVANCING = 2

# --- hyperparameters fixed by calibration (section 6) --------------------------------------------------------------
GRID: dict[str, tuple[str, tuple[float, ...]]] = {
    "A1": ("lambda", (0.1, 1.0)),
    "A2": ("u_pre", (1024.0, 2048.0)),
    "A4": ("k0_fraction", (0.125, 1.0)),
    "A5-D": ("mu", (0.1, 1.0)),
}
TAU_ADDR = 0.2  # section 4: tau_a
CENTRE_DECAY = 0.99  # A5-C: EMA decay of the batch mean of z
CENTRE_INIT_BATCHES = 16  # A5-C: m initialised over the first 16 training batches
DIVERSITY_SCALE = 2.0  # L_div = log(mean_{i != j} exp(2 q_i . q_j))
CALIBRATION_MIN_DIFFERENCE = 0.02
CALIBRATION_INIT_SEED = 1891


class Hyper(NamedTuple):
    """The four calibrated values (a value is only used by its own arm). The defaults are the worst-case
    (most expensive) grid values, used only when no calibration record exists (rehearsal)."""

    lambda_: float = 1.0
    u_pre: float = 1024.0
    k0_fraction: float = 1.0
    mu: float = 1.0

    def as_json(self) -> dict[str, float]:
        return {"lambda": self.lambda_, "u_pre": self.u_pre, "k0_fraction": self.k0_fraction, "mu": self.mu}

    @classmethod
    def from_json(cls, data: Mapping[str, Any]) -> "Hyper":
        return cls(float(data["lambda"]), float(data["u_pre"]), float(data["k0_fraction"]), float(data["mu"]))


def with_value(hyper: Hyper, arm: str, value: float) -> Hyper:
    name = GRID[arm][0]
    key = {"lambda": "lambda_", "u_pre": "u_pre", "k0_fraction": "k0_fraction", "mu": "mu"}[name]
    return hyper._replace(**{key: float(value)})


# --- updates, schedules and readouts (sections 5, 6) ------------------------------------------------------------------
UPDATES = 8192  # U
STAGE_MULTIPLIER = {1: 1, 2: 4, 3: 1}  # stage updates = multiplier * U
STAGE_SLOTS = {1: 4096, 2: 16384, 3: 65536}
STAGE_DRAWS: dict[int, tuple[int, ...]] = {1: tuple(range(1, 9)), 2: tuple(range(9, 13)), 3: (13, 14)}
INIT_SEEDS = (1901, 1902)
DIAG_EVERY = 64
PROBE_FACTS = 256
ANNEAL_FRACTION = 0.5  # T_A = stage updates / 2 (U/2 at Stage 1)
STANDARD_K = TOP  # 8


def stage_updates(stage: int, updates: int = UPDATES) -> int:
    return STAGE_MULTIPLIER[stage] * updates


def stage_readouts(stage: int, updates: int = UPDATES) -> tuple[int, ...]:
    """Update counts of the readouts: U at Stages 1 and 3, U and 4U at Stage 2 (section 5)."""
    return (updates, 4 * updates) if stage == 2 else (updates,)


def decisive_readout(stage: int, updates: int = UPDATES) -> int:
    """The readout that decides the class: 4U at Stage 2, U otherwise."""
    return stage_readouts(stage, updates)[-1]


def exposures_per_fact(updates: int, facts: int) -> float:
    """Analytical answer-site exposures per fact after ``updates`` updates (128 answer sites per update)."""
    return updates * ANSWER_SITES_PER_BATCH / facts


class Schedule(NamedTuple):
    """Updates and the scheduled-arm parameters of one cell, in updates of the run (section 5: at Stage 2
    every schedule is expressed in exposures per fact, so U_pre and T_A are multiplied by four)."""

    total: int
    u_pre: int | None  # A2
    t_anneal: int | None  # A4
    k0: int | None  # A4


def schedule_for(arm: str, stage: int, hyper: Hyper, slots: int, updates: int = UPDATES) -> Schedule:
    """U_pre of A2 and T_A, k_0 of A4 for ``arm`` at ``stage``; ``updates`` is U (the DRY stage passes a tiny
    one; U_pre scales with U / 8,192 so that the registered proportions hold). A scheduled arm at Stage 3 is
    never defined (section 5: no schedule is ever defined in updates at Stage 3)."""
    total = stage_updates(stage, updates)
    if arm in SCHEDULED_ARMS and stage == 3:
        raise ValueError("no schedule is defined at Stage 3 (ADR-0019 section 5, ruling 1)")
    if arm == "A2":
        u_pre = max(1, round(hyper.u_pre * STAGE_MULTIPLIER[stage] * updates / UPDATES))
        return Schedule(total, u_pre, None, None)
    if arm == "A4":
        return Schedule(total, None, max(1, round(ANNEAL_FRACTION * total)), min(slots, max(STANDARD_K, round(hyper.k0_fraction * slots))))
    return Schedule(total, None, None, None)


def k_schedule(t: int, k0: int, t_anneal: int) -> int:
    """A4's read width: ``max(8, round(k_0 * (8 / k_0)^(t / T_A)))`` for t < T_A, and 8 from T_A on (section 4)."""
    if t < 0:
        raise ValueError("t is a number of updates taken")
    if t >= t_anneal:
        return STANDARD_K
    return int(max(STANDARD_K, round(k0 * float(STANDARD_K / k0) ** (t / t_anneal))))


# --- thresholds (sections 6, 8) ------------------------------------------------------------------------------------------
SUCCESS_FRACTION_OF_A6 = 0.90  # condition 1
A6_MIN_ACCURACY = 0.90
DISTINCT_FRACTION = 0.50  # condition 3
LARGEST_SHARE_MAX = 0.02
HELDOUT_FRACTION = 0.90  # condition 4
ONSET_DISTINCT_MAX = 32  # collapse onset
COSINE_ONSET, COSINE_ESCAPE = 0.9, 0.5  # reported beside the slot rules, in no rule
MIN_EVALUATED = {1: 14, 2: 7}  # row 1 of the class table
MIN_SUCCESSES = {1: 4, 2: 2}  # row 3
MAX_FAILED_RELIABLE = 1  # row 2
LM_MARGIN = 0.05  # over A6's relative rise on the same draw and size (R1)
LM_FLAGGED_CELLS = 1  # an arm flagged in more than this many cells prints LM CAPABILITY REDUCED
PAIRED_THRESHOLD = 4
BEATS_DENSE_RATIO = 1.10
DENSE_CEILING = 0.909
SUPERVISION_DROP = 0.10
SUPERVISION_WINDOW = 512
RECALL_THRESHOLD, STABLE_THRESHOLD = 0.90, 0.80
H19A_ONSET_UPDATES = 256
H19A_CELLS = 12
H19A_RATIO = 0.01
H19A_RATIO_FROM, H19A_RATIO_TO = 64, 1024
SUSTAINED_DROP = 0.05
READOUT_MIN_A6 = 0.90

# --- resources and budgets (section 10) -----------------------------------------------------------------------------------
RSS_WORKER_BYTES = p9core.RSS_WORKER_BYTES  # 3 GiB
RSS_AGGREGATE_BYTES = p9core.RSS_AGGREGATE_BYTES  # 24 GiB
WORKERS = 6
BUDGET_A_HOURS, BUDGET_B_HOURS = 4.0, 3.0
HEADROOM = 2.0  # twice the projection must fit
REHEARSAL_UPDATES = 256
BUDGET_OF_STAGE: dict[str, str] = {  # the stages charged to Budget A (4 h) and Budget B (3 h)
    "generate": "A", "calibrate": "A", "rehearse": "A", "gates": "A", "stage1": "A", "stagegate": "A", "analyze": "A", "report": "A",
    "stage2": "B", "stage3": "B",
}  # fmt: skip

# --- run directories and records --------------------------------------------------------------------------------------------------
STAGE_CODES: dict[str, str] = {
    "generate": "P", "drawplan": "L", "calibrate": "C", "rehearse": "H", "gates": "G", "train": "T", "evaluate": "E",
    "stagegate": "S", "analyze": "A", "report": "R", "dry": "D",
}  # fmt: skip
RECORD_KINDS = (
    "train", "snapshot", "eval", "stage_manifest", "calibration", "rehearsal", "analysis", "data_manifest", "gates",
    "draw_plan", "stage_gate", "projection", "ledger",
)  # fmt: skip
PANELS = ("A", "B")
PANEL_STREAM = {"A": "panel_a", "B": "panel_b"}


# --- cells (sections 5, 6) -----------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Cell:
    """One cell. ``stage`` is 1, 2, 3 or 0 (calibration); ``draw`` the registered draw 1..14 (calibration: the
    rehearsal seed set 3 or 4; test cells: 1); ``seed_index`` is j (init seed 1901 + j); ``value`` the grid value
    of a calibration cell (None elsewhere)."""

    stage: int
    arm: str
    slots: int
    draw: int
    seed_index: int
    value: float | None
    label: str

    def __post_init__(self) -> None:
        if self.arm not in ARMS or self.slots not in SLOTS_BY_SIZE or self.seed_index not in (0, 1) or self.stage not in (0, 1, 2, 3):
            raise ValueError(f"unregistered P9II cell: {self.label}")

    @property
    def facts(self) -> int:
        return FACTS_PROPORTIONAL[self.slots]

    @property
    def learned(self) -> bool:
        return self.arm in LEARNED_ARMS

    @property
    def init_seed(self) -> int:
        return (CALIBRATION_INIT_SEED if self.stage == 0 else INIT_SEEDS[0]) + self.seed_index


def _fmt(value: float) -> str:
    return f"{value:g}"


def make_label(stage: int, arm: str, slots: int, draw: int, j: int, value: float | None = None, prefix: str = "") -> str:
    if stage == 0:
        extra = "" if value is None else f"-v{_fmt(value)}"
        return f"{prefix}CAL-{arm}{extra}-n{slots}-d{draw}-j{j}"
    return f"{prefix}S{stage}-{arm}-n{slots}-d{draw:02d}-j{j}"


def _cell(stage: int, arm: str, draw: int, j: int, value: float | None = None) -> Cell:
    slots = 4096 if stage == 0 else STAGE_SLOTS[stage]
    return Cell(stage, arm, slots, draw, j, value, make_label(stage, arm, slots, draw, j, value))


def stage1_cells() -> list[Cell]:
    """128 cells: seven learned arms x draws 1-8 x 2 seeds, A6 and A7 x draws 1-8 x 1 seed (section 5)."""
    out = [_cell(1, a, d, j) for a in LEARNED_ARMS for d in STAGE_DRAWS[1] for j in (0, 1)]
    out += [_cell(1, a, d, 0) for a in REFERENCE_ARMS for d in STAGE_DRAWS[1]]
    return out


def stage2_arms(advancing: Sequence[str]) -> list[str]:
    """Learned arms of a Stage 2 configuration: A0, the advancing arms in the order given, and A1-S when A1 or
    A2 advances. ``advancing`` holds at most two arms and never A0 or A1-S."""
    adv = list(advancing)
    if len(adv) > MAX_ADVANCING or len(set(adv)) != len(adv) or any(a not in ADVANCE_ORDER for a in adv):
        raise ValueError(f"a Stage 2 configuration advances at most two distinct arms of {ADVANCE_ORDER}: {adv}")
    arms = ["A0", *adv]
    if any(a in SUPERVISED_ARMS for a in adv):
        arms.append("A1-S")
    return arms


def stage2_cells(advancing: Sequence[str]) -> list[Cell]:
    """16 to 40 cells: the learned arms x draws 9-12 x 2 seeds, A6 and A7 x draws 9-12 x 1 seed."""
    out = [_cell(2, a, d, j) for a in stage2_arms(advancing) for d in STAGE_DRAWS[2] for j in (0, 1)]
    out += [_cell(2, a, d, 0) for a in REFERENCE_ARMS for d in STAGE_DRAWS[2]]
    return out


def stage3_cells(selected: str) -> list[Cell]:
    """6 or 8 cells: A0, the selected arm (if not A0), A6, A7 x draws 13-14 x one seed. Only a constant-objective
    arm may be selected."""
    if selected not in CONSTANT_OBJECTIVE_ARMS or selected in REFERENCE_ARMS or selected == "A1-S":
        raise ValueError(f"Stage 3 runs only a constant-objective selected arm (A0, A1, A5-C, A5-D): {selected!r}")
    arms = ["A0"] if selected == "A0" else ["A0", selected]
    return [_cell(3, a, d, 0) for a in [*arms, *REFERENCE_ARMS] for d in STAGE_DRAWS[3]]


CALIBRATION_DRAWS = (3, 4)


def calibration_cells() -> list[Cell]:
    """22 cells: each grid value of A1, A2, A4 and A5-D on calibration draws 3 and 4 (16 cells), and A0, A6, A7 on
    the same draws (6 cells), one initialization seed, 4,096 slots (section 6)."""
    out = [_cell(0, arm, d, 0, value) for arm, (_, values) in GRID.items() for value in values for d in CALIBRATION_DRAWS]
    out += [_cell(0, arm, d, 0) for arm in ("A0", "A6", "A7") for d in CALIBRATION_DRAWS]
    return out


def _all_stage_cells() -> list[Cell]:
    every = [*stage1_cells(), *stage2_cells(list(ADVANCE_ORDER[:2])), *stage2_cells(["A2", "A1"]), *stage2_cells(["A5-C", "A4"]), *stage2_cells([])]
    for selected in ("A0", "A1", "A5-C", "A5-D"):
        every += stage3_cells(selected)
    unique = {c.label: c for c in every}
    return list(unique.values())


STAGE1_CELL_COUNT, STAGE2_MAX_CELLS, STAGE2_MIN_CELLS, STAGE3_MAX_CELLS, CALIBRATION_CELL_COUNT = 128, 40, 16, 8, 22


def _assert_registry() -> None:
    if len(stage1_cells()) != STAGE1_CELL_COUNT or len(calibration_cells()) != CALIBRATION_CELL_COUNT:
        raise ImportError("P9II registry counts differ from sections 5 and 6")
    counts = {tuple(adv): len(stage2_cells(adv)) for adv in ([], ["A5-C"], ["A2"], ["A5-C", "A5-D"], ["A5-C", "A2"], ["A2", "A1"])}
    if counts != {(): 16, ("A5-C",): 24, ("A2",): 32, ("A5-C", "A5-D"): 32, ("A5-C", "A2"): 40, ("A2", "A1"): 40}:
        raise ImportError("P9II Stage 2 counts differ from section 5 (16 / 24 / 32 / 40)")
    if {len(stage3_cells("A0")), len(stage3_cells("A5-C"))} != {6, 8}:
        raise ImportError("P9II Stage 3 counts differ from section 5")
    labels = [c.label for c in stage1_cells()] + [c.label for c in calibration_cells()]
    if len(set(labels)) != len(labels):
        raise ImportError("P9II cell labels are not unique")


_assert_registry()
_BY_LABEL: dict[str, Cell] = {c.label: c for c in [*_all_stage_cells(), *calibration_cells()]}
_TEST_LABEL = re.compile(r"^TEST-(?:CAL-(?P<carm>A[0-9](?:-[A-Z])?)(?:-v(?P<val>[0-9.e+-]+))?-n(?P<cslots>\d+)-d(?P<cdraw>\d+)-j(?P<cj>\d)|S(?P<stage>\d)-(?P<arm>A[0-9](?:-[A-Z])?)-n(?P<slots>\d+)-d(?P<draw>\d+)-j(?P<j>\d))$")


def make_cell(arm: str, slots: int, stage: int = 1, draw: int = 1, j: int = 0, value: float | None = None) -> Cell:
    """A cell of any arm at any size without consulting the registry (unit tests, the DRY stage, rehearsal)."""
    return Cell(stage, arm, slots, draw, j, value, make_label(stage, arm, slots, draw, j, value, "TEST-"))


def parse_label(label: str) -> Cell:
    """The registered or calibration cell named ``label``; ``TEST-`` labels (``make_cell``) are rebuilt. ValueError
    otherwise."""
    cell = _BY_LABEL.get(label)
    if cell is not None:
        return cell
    match = _TEST_LABEL.match(label)
    if match is None:
        raise ValueError(f"unknown P9II cell label {label!r}")
    if match["carm"]:
        return make_cell(match["carm"], int(match["cslots"]), 0, int(match["cdraw"]), int(match["cj"]), None if match["val"] is None else float(match["val"]))
    return make_cell(match["arm"], int(match["slots"]), int(match["stage"]), int(match["draw"]), int(match["j"]))


def labels_of(items: Sequence[Cell]) -> list[str]:
    return [c.label for c in items]


# --- seeds (section 7) ------------------------------------------------------------------------------------------------------------------
REGISTERED_BASE = 190001
DRAW_STRIDE = 100
RESERVE_BASES = {1: 191401, 2: 191501}
TARGET_OFFSET, STREAM_OFFSET = 40, 60
CALIBRATION_SEED_SETS = (3, 4)  # rehearsal seed sets of the P9 namespace (179301+, 179401+)
REHEARSAL_SEED_SET = 5  # 179501+
TEST_SEED_BASE, TEST_SEED_TOP = 910001, 919999
P9I_TEST_RANGE = (900001, 909999)
RESERVED_LATER = ((200001, 229999), (920001, 929999))
P9_REHEARSAL_DRAWS = tuple(range(10))
RANGES = {"p9ii_test": (TEST_SEED_BASE, TEST_SEED_TOP), "p9i_test": P9I_TEST_RANGE, "later_a": RESERVED_LATER[0], "later_b": RESERVED_LATER[1]}


def _seed_set(name: str, base: int, *, registered_layout: bool) -> p9core.SeedSet:
    """Layout inside a set: base + 0..13 the fourteen data seeds in P9's order; registered sets put the Panel A
    null seeds at base + 14..16 and Panel B's at base + 17..19 (P9-I's registered convention); the other sets use
    base + 20..22 and base + 30..32 (P9's rehearsal convention)."""
    values = {n: base + i for i, n in enumerate(p9core.DATA_SEEDS)}
    a0, b0 = (14, 17) if registered_layout else (20, 30)
    return p9core.SeedSet(name, **values, null_seeds_a=tuple(base + a0 + i for i in range(3)), null_seeds_b=tuple(base + b0 + i for i in range(3)))


def draw_base(draw: int) -> int:
    if not 1 <= draw <= 14:
        raise ValueError("registered draws are 1..14")
    return REGISTERED_BASE + DRAW_STRIDE * (draw - 1)


def registered_draw_seeds(draw: int) -> p9core.SeedSet:
    """``p9ii-draw-<k>``, base seeds 190001, 190101, ..., 191301."""
    return _seed_set(f"p9ii-draw-{draw}", draw_base(draw), registered_layout=True)


def reserve_seeds(reserve: int) -> p9core.SeedSet:
    """``p9ii-reserve-1`` (191401) and ``p9ii-reserve-2`` (191501)."""
    return _seed_set(f"p9ii-reserve-{reserve}", RESERVE_BASES[reserve], registered_layout=True)


def calibration_seeds(draw: int) -> p9core.SeedSet:
    if draw not in CALIBRATION_SEED_SETS:
        raise ValueError(f"calibration uses rehearsal seed sets {CALIBRATION_SEED_SETS} only")
    return p9core.rehearsal_seeds(draw)


def rehearsal_seeds() -> p9core.SeedSet:
    return p9core.rehearsal_seeds(REHEARSAL_SEED_SET)


def test_seeds(offset: int = 0) -> p9core.SeedSet:
    """Seeds for unit tests and the DRY stage: 910001 upward (900001 upward is P9-I's test namespace)."""
    base = TEST_SEED_BASE + 100 * offset
    if base + 99 > TEST_SEED_TOP:
        raise ValueError("test seed offset out of range")
    return _seed_set(f"p9ii-test-{offset}", base, registered_layout=False)


def seed_values(s: p9core.SeedSet, *, inits: Sequence[int] = ()) -> frozenset[int]:
    """Every integer a seed set uses: data and null seeds, and the target-slot and A1-S stream seeds of
    j = 0 and 1 (base + 40 + j, base + 60 + j)."""
    base = s.facts
    derived = [base + TARGET_OFFSET + j for j in (0, 1)] + [base + STREAM_OFFSET + j for j in (0, 1)]
    return frozenset([*s.data_values(), *s.null_seeds_a, *s.null_seeds_b, *derived, *inits])


def target_seed(seeds: p9core.SeedSet, j: int) -> int:
    return seeds.facts + TARGET_OFFSET + j


def stream_seed(seeds: p9core.SeedSet, j: int) -> int:
    return seeds.facts + STREAM_OFFSET + j


def seed_namespaces() -> dict[str, frozenset[int]]:
    """P9II's ranges and the ranges of P9 and P9-I, by name (the disjointness test and G1's check read it)."""
    p9i_inits = frozenset([*p9icore.INIT_SEEDS, *p9icore.CALIBRATION_INIT_SEEDS])
    return {
        "registered": frozenset().union(*(seed_values(registered_draw_seeds(k)) for k in range(1, 15))),
        "reserve": frozenset().union(*(seed_values(reserve_seeds(r)) for r in (1, 2))),
        "init": frozenset(INIT_SEEDS),
        "calibration_init": frozenset({CALIBRATION_INIT_SEED, CALIBRATION_INIT_SEED + 1}),
        "calibration_data_3": seed_values(calibration_seeds(3)),
        "calibration_data_4": seed_values(calibration_seeds(4)),
        "rehearsal_data_5": seed_values(rehearsal_seeds()),
        "test": frozenset().union(*(seed_values(test_seeds(k)) for k in range(3))),
        "p9_registered": p9core.registered_seed_values(),
        "p9i_registered": p9icore.registered_seed_values() | p9i_inits,
        "p9_rehearsal_other": frozenset().union(
            *(seed_values(p9core.rehearsal_seeds(k)) for k in P9_REHEARSAL_DRAWS if k not in (*CALIBRATION_SEED_SETS, REHEARSAL_SEED_SET))
        ),
    }


def assert_namespaces_disjoint(namespaces: Mapping[str, frozenset[int]] | None = None) -> None:
    """The registered, reserve, calibration, rehearsal and test ranges are disjoint from each other, from every
    seed used by P9 and P9-I and from the ranges reserved for later studies (section 7)."""
    ns = dict(namespaces or seed_namespaces())
    names = sorted(ns)
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            common = ns[a] & ns[b]
            if common:
                raise ValueError(f"seed namespaces {a!r} and {b!r} overlap: {sorted(common)[:5]}")
    for name, (low, high) in RANGES.items():
        for other, values in ns.items():
            inside = sorted(v for v in values if low <= v <= high)
            if inside and not (name == "p9ii_test" and other == "test"):
                raise ValueError(f"namespace {other!r} uses {inside[:3]} inside the reserved range {name!r} {low}-{high}")
    for v in ns["test"]:
        if not TEST_SEED_BASE <= v <= TEST_SEED_TOP:
            raise ValueError(f"test seed {v} lies outside 910001-919999")


assert_namespaces_disjoint()

SEED_MODES = ("registered", "calibration", "rehearsal")


def check_seed_set(mode: str, seed_set_name: str) -> None:
    """``registered``: only ``p9ii-draw-k`` and ``p9ii-reserve-k``; ``calibration``: only rehearsal sets 3 and 4;
    ``rehearsal``: only rehearsal set 5; unit tests and the DRY stage use test seeds in the calibration or
    rehearsal modes. Anything else is refused."""
    if mode not in SEED_MODES:
        raise ValueError(f"unknown mode {mode!r}")
    if mode == "registered":
        ok = bool(re.fullmatch(r"p9ii-(draw|reserve)-\d+", seed_set_name))
    elif mode == "calibration":
        ok = seed_set_name in {f"rehearsal-{k}" for k in CALIBRATION_SEED_SETS} or seed_set_name.startswith("p9ii-test")
    else:
        ok = seed_set_name == f"rehearsal-{REHEARSAL_SEED_SET}" or seed_set_name.startswith("p9ii-test")
    if not ok:
        raise ValueError(f"mode {mode!r} cannot use the {seed_set_name!r} seed set")


# --- draws, G1 and reserve substitution (section 9) ---------------------------------------------------------------------------------------
DRAW_NAMES = tuple(f"p9ii-draw-{k}" for k in range(1, 15))
RESERVE_NAMES = ("p9ii-reserve-1", "p9ii-reserve-2")
MAX_REPLACEMENTS = 2


class DrawPlan(NamedTuple):
    """Which seed set serves each registered draw slot. ``replacements`` maps a failed slot to the reserve that took its
    place; ``ok`` is False (and ``reason`` set) when nothing may run and the matter returns to the human lead."""

    ok: bool
    seed_set_of: dict[int, str]
    replacements: dict[int, str]
    reason: str | None


def plan_draws(g1_passed: Mapping[str, bool]) -> DrawPlan:
    """Section 9: a registered draw that fails G1 is replaced by the next unused reserve, ``p9ii-reserve-1`` then
    ``p9ii-reserve-2``, taking the failed draw's place and stage. If a reserve fails G1 (when it is needed), or more than
    two draws need replacing, nothing is run. A draw or a reserve with no G1 result counts as failed."""
    failed = [k for k in range(1, 15) if g1_passed.get(DRAW_NAMES[k - 1]) is not True]
    seed_set_of = {k: DRAW_NAMES[k - 1] for k in range(1, 15)}
    if len(failed) > MAX_REPLACEMENTS:
        return DrawPlan(False, seed_set_of, {}, f"{len(failed)} draws failed G1 (at most {MAX_REPLACEMENTS} may be replaced)")
    replacements: dict[int, str] = {}
    for slot, reserve in zip(failed, RESERVE_NAMES, strict=False):
        if g1_passed.get(reserve) is not True:
            return DrawPlan(False, seed_set_of, replacements, f"reserve {reserve} failed G1 or has no G1 result")
        replacements[slot] = reserve
        seed_set_of[slot] = reserve
    return DrawPlan(True, seed_set_of, replacements, None)


def seeds_of_name(name: str) -> p9core.SeedSet:
    m = re.fullmatch(r"p9ii-(draw|reserve)-(\d+)", name)
    if m is None:
        raise ValueError(f"not a registered P9II seed set name: {name!r}")
    return registered_draw_seeds(int(m[2])) if m[1] == "draw" else reserve_seeds(int(m[2]))


# --- the calibration rule (section 6) -------------------------------------------------------------------------------------------------------
def select_value(values: Sequence[float], min_accuracy: Mapping[float, float], median_first_success: Mapping[float, float]) -> float:
    """The value with the higher minimum accuracy over the two calibration draws. A tie, or a difference below 0.02,
    goes to the secondary criterion: the earlier median over the two draws of the time to first success (a cell that never
    succeeds counts as later than any that does; ``math.inf``). If that is also tied, the first value listed."""
    best = max(min_accuracy[v] for v in values)
    contenders = [v for v in values if best - min_accuracy[v] < CALIBRATION_MIN_DIFFERENCE]
    if len(contenders) == 1:
        return contenders[0]
    earliest = min(median_first_success[v] for v in contenders)
    return next(v for v in contenders if median_first_success[v] == earliest)


def median(values: Sequence[float]) -> float:
    s = sorted(values)
    n = len(s)
    if n == 0:
        return math.nan
    mid = n // 2
    if n % 2:
        return float(s[mid])
    if math.isinf(s[mid - 1]) and math.isinf(s[mid]) and s[mid - 1] == s[mid]:
        return float(s[mid])
    return float((s[mid - 1] + s[mid]) / 2)


# --- config -----------------------------------------------------------------------------------------------------------------------------------
def registered_config() -> dict[str, Any]:
    """The configuration mirrored in ``configs/p9ii_addressing.toml`` (derived from the constants)."""
    return {
        "schema_version": SCHEMA,
        "experiment_family": FAMILY,
        "spec_reference": SPEC,
        "memory": {"key_width": KEY_WIDTH, "top": TOP, "temperature": TEMPERATURE, "slots": list(SLOTS_BY_SIZE), "facts": [FACTS_PROPORTIONAL[s] for s in SLOTS_BY_SIZE], "window": WINDOW},
        "training": {
            "learning_rate": LEARNING_RATE, "clip_norm": CLIP_NORM, "batch_contexts": BATCH_CONTEXTS, "updates": UPDATES,
            "loss": "alphabet cross-entropy at answer sites (32 symbols 0x40-0x5F)", "diag_every": DIAG_EVERY, "probe_facts": PROBE_FACTS,
            "tau_addr": TAU_ADDR, "centre_decay": CENTRE_DECAY, "centre_init_batches": CENTRE_INIT_BATCHES, "diversity_scale": DIVERSITY_SCALE,
            "anneal_fraction": ANNEAL_FRACTION,
        },
        "arms": {"learned": list(LEARNED_ARMS), "reference": list(REFERENCE_ARMS), "advance_order": list(ADVANCE_ORDER), "carry_forward_order": list(CARRY_FORWARD_ORDER), "max_advancing": MAX_ADVANCING},
        "grid": {arm: {"hyperparameter": name, "values": list(values)} for arm, (name, values) in GRID.items()},
        "calibration": {"draws": list(CALIBRATION_DRAWS), "init_seed": CALIBRATION_INIT_SEED, "min_difference": CALIBRATION_MIN_DIFFERENCE, "cells": CALIBRATION_CELL_COUNT},
        "stages": {
            "slots": [STAGE_SLOTS[s] for s in (1, 2, 3)], "multiplier": [STAGE_MULTIPLIER[s] for s in (1, 2, 3)],
            "draws_first": [STAGE_DRAWS[s][0] for s in (1, 2, 3)], "draws_last": [STAGE_DRAWS[s][-1] for s in (1, 2, 3)],
            "stage1_cells": STAGE1_CELL_COUNT, "stage2_max_cells": STAGE2_MAX_CELLS, "stage2_min_cells": STAGE2_MIN_CELLS, "stage3_max_cells": STAGE3_MAX_CELLS,
        },
        "seeds": {
            "registered_base": REGISTERED_BASE, "draw_stride": DRAW_STRIDE, "reserve_bases": [RESERVE_BASES[1], RESERVE_BASES[2]],
            "init": list(INIT_SEEDS), "target_offset": TARGET_OFFSET, "stream_offset": STREAM_OFFSET,
            "calibration_seed_sets": list(CALIBRATION_SEED_SETS), "rehearsal_seed_set": REHEARSAL_SEED_SET, "test_base": TEST_SEED_BASE, "test_top": TEST_SEED_TOP,
        },
        "thresholds": {
            "success_fraction_of_a6": SUCCESS_FRACTION_OF_A6, "a6_min_accuracy": A6_MIN_ACCURACY, "distinct_fraction": DISTINCT_FRACTION,
            "largest_share_max": LARGEST_SHARE_MAX, "heldout_fraction": HELDOUT_FRACTION, "onset_distinct_max": ONSET_DISTINCT_MAX,
            "cosine_onset": COSINE_ONSET, "cosine_escape": COSINE_ESCAPE, "lm_margin": LM_MARGIN, "paired_threshold": PAIRED_THRESHOLD,
            "beats_dense_ratio": BEATS_DENSE_RATIO, "dense_ceiling": DENSE_CEILING, "supervision_drop": SUPERVISION_DROP, "supervision_window": SUPERVISION_WINDOW,
            "recall_threshold": RECALL_THRESHOLD, "stable_threshold": STABLE_THRESHOLD, "sustained_drop": SUSTAINED_DROP,
            "h19a_onset_updates": H19A_ONSET_UPDATES, "h19a_cells": H19A_CELLS, "h19a_ratio": H19A_RATIO,
            "min_evaluated_stage1": MIN_EVALUATED[1], "min_evaluated_stage2": MIN_EVALUATED[2], "min_successes_stage1": MIN_SUCCESSES[1], "min_successes_stage2": MIN_SUCCESSES[2],
        },
        "resources": {"rss_worker_bytes": RSS_WORKER_BYTES, "rss_aggregate_bytes": RSS_AGGREGATE_BYTES, "workers": WORKERS, "budget_a_hours": BUDGET_A_HOURS, "budget_b_hours": BUDGET_B_HOURS, "headroom": HEADROOM, "rehearsal_updates": REHEARSAL_UPDATES},
    }


def validate_config(data: dict[str, Any]) -> dict[str, Any]:
    _validate(data, registered_config(), "P9II config")
    return data


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_config(path: Path | None = None) -> dict[str, Any]:
    with (path or repo_root() / DEFAULT_CONFIG).open("rb") as stream:
        return validate_config(tomllib.load(stream))


def render_config_toml() -> str:
    """The canonical text of ``configs/p9ii_addressing.toml`` (a test requires byte equality)."""
    from studies.p9i.core import _toml_lines

    header = [
        "# ADR-0019 revision 4 (P9II) registered constants. Generated by studies.p9ii.core.render_config_toml",
        "# and validated against studies.p9ii.core; any difference is refused.",
        "",
    ]
    return "\n".join([*header, *_toml_lines(registered_config(), "")]) + "\n"


# --- identity hashes -------------------------------------------------------------------------------------------------------------------------------
def source_hashes(root: Path | None = None) -> dict[str, str]:
    """SHA-256 of every ``studies/p9ii/*.py`` and launch script, of the imported ``studies/p9i`` modules and of the imported
    ``studies/p9`` modules."""
    base = root or repo_root()
    out: dict[str, str] = {}
    for p in sorted((base / "studies" / "p9ii").glob("*.py")):
        out[f"studies/p9ii/{p.name}"] = file_sha256(p)
    for p in sorted((base / LAUNCH_DIR).glob("*.sh")):
        out[f"studies/p9ii/launch/{p.name}"] = file_sha256(p)
    for name in IMPORTED_P9I_MODULES:
        out[f"studies/p9i/{name}.py"] = file_sha256(base / "studies" / "p9i" / f"{name}.py")
    for name in IMPORTED_P9_MODULES:
        out[f"studies/p9/{name}.py"] = file_sha256(base / "studies" / "p9" / f"{name}.py")
    return out


def source_digest(root: Path | None = None) -> str:
    return sha256(canonical_json(source_hashes(root)))


def spec_sha256(root: Path | None = None) -> str:
    return file_sha256((root or repo_root()) / SPEC)


def config_sha256(path: Path | None = None) -> str:
    return sha256(canonical_json(load_config(path)))


class Identity(NamedTuple):
    source_sha256: str
    spec_sha256: str
    config_sha256: str
    frozen_source_sha256: str  # arborlm.p8_core.source_digest()

    def as_dict(self) -> dict[str, str]:
        return self._asdict()


def code_identity(root: Path | None = None) -> dict[str, str]:
    from arborlm import p8_core

    base = root or repo_root()
    return Identity(source_digest(base), spec_sha256(base), config_sha256(base / DEFAULT_CONFIG), p8_core.source_digest()).as_dict()


def environment() -> dict[str, Any]:
    """Operating system, machine, processor, Python and torch versions and thread settings (every run manifest
    carries it: the consolidation review found that P9-I's registered manifests did not)."""

    def version(package: str) -> str | None:
        try:
            return metadata.version(package)
        except metadata.PackageNotFoundError:
            return None

    return {
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python": sys.version,
        "python_implementation": platform.python_implementation(),
        "torch": torch.__version__,
        "psutil": version("psutil"),
        "cpu_count": os.cpu_count(),
        "threads": {
            "torch_num_threads": torch.get_num_threads(),
            "torch_interop_threads": torch.get_num_interop_threads(),
            "deterministic_algorithms": bool(torch.are_deterministic_algorithms_enabled()),
            "env": {k: os.environ.get(k) for k in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "PYTHONHASHSEED")},
        },
    }


# --- run names, records and paths ---------------------------------------------------------------------------------------------------------------------
def utc_stamp(now: datetime | None = None) -> str:
    return (now or datetime.now(UTC)).strftime("%Y%m%dT%H%M%S%fZ")


def run_name(stage: str, now: datetime | None = None, unique: str | None = None) -> str:
    """``P9II<code>-<utc>-<uuid hex>`` for a stage in ``STAGE_CODES``."""
    if stage not in STAGE_CODES:
        raise ValueError(f"unknown P9II stage {stage!r}")
    return f"P9II{STAGE_CODES[stage]}-{utc_stamp(now)}-{unique or uuid.uuid4().hex}"


def parse_run_name(name: str) -> tuple[str, str, str]:
    head, _, rest = name.partition("-")
    stamp, _, unique = rest.partition("-")
    codes = {code: stage for stage, code in STAGE_CODES.items()}
    if not head.startswith("P9II") or head[4:] not in codes or not stamp.endswith("Z") or not unique:
        raise ValueError(f"not a P9II run name: {name!r}")
    return codes[head[4:]], stamp, unique


def envelope(kind: str) -> dict[str, Any]:
    if kind not in RECORD_KINDS:
        raise ValueError(f"unknown record kind {kind!r}")
    return {"kind": kind, "schema": SCHEMA, "study": STUDY}


def write_record(path: Path, record: Mapping[str, Any]) -> None:
    """Atomically write a JSON record (canonical, no NaN) after checking its envelope keys."""
    if record.get("study") != STUDY or record.get("schema") != SCHEMA or record.get("kind") not in RECORD_KINDS:
        raise ValueError("P9II record needs study, schema and a registered kind")
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, dict(record))


def read_record(path: Path, kind: str | None = None) -> dict[str, Any]:
    record = read_json(path)
    if not isinstance(record, dict) or record.get("study") != STUDY or record.get("schema") != SCHEMA:
        raise ValueError(f"not a P9II record: {path}")
    if kind is not None and record.get("kind") != kind:
        raise ValueError(f"expected a {kind!r} record, got {record.get('kind')!r}: {path}")
    return record


def cell_dir(run_dir: Path, label: str) -> Path:
    parse_label(label)
    return run_dir / "cells" / label


def snapshot_stem(update: int) -> str:
    return f"u{update:07d}"


def eval_path(run_dir: Path, label: str, update: int) -> Path:
    return cell_dir(run_dir, label) / "eval" / snapshot_stem(update) / "eval.json"


def default_experiments_root() -> Path:
    return p9core.default_experiments_root()


# --- the two charged-time ledgers (Budget A and Budget B, section 10) ---------------------------------------------------------------------------------------
class LedgerRefused(RuntimeError):
    """A stage cannot start: the remainder of its budget is smaller than the stage's own cap."""


class Ledger:
    """Charged wall time of one budget. Entries are appended to one JSON file; nothing is ever removed. A stage refuses to
    start when the remainder of the cap is smaller than its own stage cap, and is charged what it used. Budget A
    (4 h) carries calibration, rehearsal, the gates, generation and Stage 1; Budget B (3 h) carries Stages 2 and 3, and
    Budget A's unused time never moves to it."""

    def __init__(self, path: Path, budget: str, cap_seconds: float | None = None) -> None:
        if budget not in ("A", "B"):
            raise ValueError("budget is A or B")
        self.path, self.budget = path, budget
        self.cap_seconds = cap_seconds if cap_seconds is not None else (BUDGET_A_HOURS if budget == "A" else BUDGET_B_HOURS) * 3600.0

    def entries(self) -> list[dict[str, Any]]:
        if not self.path.is_file():
            return []
        data = read_json(self.path)
        if not isinstance(data, dict) or data.get("study") != STUDY or data.get("budget") != self.budget:
            raise ValueError(f"not a P9II ledger of budget {self.budget}: {self.path}")
        return list(data["entries"])

    def charged(self) -> float:
        return float(sum(float(e["seconds"]) for e in self.entries()))

    def remaining(self) -> float:
        return max(0.0, self.cap_seconds - self.charged())

    def require_room(self, stage: str, stage_cap_seconds: float) -> None:
        if stage_cap_seconds <= 0:
            raise LedgerRefused(f"stage {stage}: the stage cap must be positive")
        if self.remaining() < stage_cap_seconds:
            raise LedgerRefused(
                f"stage {stage}: {self.remaining():.0f} s of Budget {self.budget} ({self.cap_seconds:.0f} s) remain, less than the "
                f"stage cap of {stage_cap_seconds:.0f} s; the work stops and returns to the human lead"
            )

    def charge(self, stage: str, run: str, seconds: float) -> None:
        entries = self.entries()
        entries.append({"stage": stage, "run": run, "seconds": max(0.0, float(seconds)), "utc": datetime.now(UTC).isoformat()})
        self.path.parent.mkdir(parents=True, exist_ok=True)
        write_json(self.path, {"study": STUDY, "kind": "ledger", "budget": self.budget, "cap_seconds": self.cap_seconds, "entries": entries})


def ledger_for_stage(stage: str, root: Path) -> Ledger:
    """The ledger a stage is charged to (``BUDGET_OF_STAGE``): ``<root>/P9II-ledger-A.json`` or ``-B.json``."""
    budget = BUDGET_OF_STAGE[stage]
    return Ledger(root / f"P9II-ledger-{budget}.json", budget)


# --- non-finite numbers in records (P9-I's reading, after its fixes) -------------------------------------------------------------------------------------------
NONFINITE = p9icore.NONFINITE
nonfinite_str = p9icore.nonfinite_str
jsonable = p9icore.jsonable
number = p9icore.number


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def derive_seed(seed: int, *tags: object) -> int:
    """A 62-bit seed derived from ``seed`` and tags (SHA-256); used for streams that must be pure functions of (seed, update)."""
    text = "|".join([str(seed), "p9ii", *map(str, tags)]).encode()
    return int.from_bytes(hashlib.sha256(text).digest()[:8], "little") & ((1 << 62) - 1)


def json_line(record: Mapping[str, Any]) -> str:
    return json.dumps(jsonable(dict(record)), allow_nan=False, sort_keys=True)
