# ruff: noqa: E501
"""P10S1 shared contract: the constants of ADR-0021 revision 4, the registry of trained cells (30 configurations per replicate, 150 registered cells,
the seed block, the optional overload row and lane L), seeds and gate G9, snapshot schedules, the config (the charged-hour cap is a config value), identity
hashes, record IO, run manifests with the environment and the one charged-time ledger. Nothing here trains or evaluates a model.

Specification: ``docs/decisions/ADR-0021-p10-s1-useful-capacity-scaling.md`` (design revision 4). Every number below is copied from the ADR with its
section. Status: implementation self-checked only. Not independent review, not Astra validation, not human approval. Astra review: NOT_PERFORMED.
"""

import functools
import hashlib
import json
import math
import os
import platform
import re
import sys
import tomllib
import uuid
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path
from typing import Any, NamedTuple

import torch

from arborlm.config import _validate
from arborlm.io import canonical_json, file_sha256, read_json, sha256, write_json
from studies.p9 import core as p9core
from studies.p9i import core as p9icore


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


# --- identity of the study ---------------------------------------------------------------------------------------
SPEC = "docs/decisions/ADR-0021-p10-s1-useful-capacity-scaling.md"
STUDY = "P10S1"
FAMILY = "P10S1_USEFUL_CAPACITY_SCALING"
SCHEMA = 1
DEFAULT_CONFIG = Path("configs/p10s1_capacity.toml")
LAUNCH_DIR = Path("studies/p10s1/launch")
FREEZE_DIR = Path("studies/p10s1/freeze")

# Modules of other studies whose code this study imports and runs; hashed into the source digest (a test scans the p10s1 sources and fails when a
# studies.p9, studies.p9i or studies.p9ii module is imported that is not listed).
IMPORTED_P9_MODULES = ("__init__", "controls", "core", "data", "evaluate", "layout", "model", "pool", "sim", "train")
IMPORTED_P9I_MODULES = ("__init__", "core", "model", "stages", "train")
IMPORTED_P9II_MODULES = ("__init__",)

# --- the tag every positive label carries (ADR-0021 section 3 item 4) ---------------------------------------------
STORE_ONLY_TAG = "STORE ONLY; ORACLE-ADDRESSED"
ORACLE_SENTENCE = "addressing was supplied by an oracle"

# --- the task and the memory (section 4; imported from P9 so there is one namespace) -------------------------------
ALPHABET = p9core.ALPHABET
ALPHABET_SIZE = p9core.ALPHABET_SIZE
ALPHABET_BASE = ALPHABET[0]
CONTEXT_BYTES, INPUT_LENGTH = p9core.CONTEXT_BYTES, p9core.INPUT_LENGTH
RECORD_BYTES, RECORDS_PER_CONTEXT = p9core.RECORD_BYTES, p9core.RECORDS_PER_CONTEXT
ANSWER_SITES_PER_CONTEXT = p9core.ANSWER_SITES_PER_CONTEXT
ANSWER_SITE_POSITIONS = p9core.ANSWER_SITE_POSITIONS
BATCH_CONTEXTS = p9core.BATCH_CONTEXTS  # 16 contexts = 128 answer-site exposures
ANSWER_SITES_PER_BATCH = p9core.ANSWER_SITES_PER_BATCH
KEY_WIDTH, TOP, TEMPERATURE = p9core.KEY_WIDTH, p9core.TOP, p9core.TEMPERATURE
HIDDEN_WIDTH = p9core.HIDDEN_WIDTH  # 32 (value width)
LEARNING_RATE, CLIP_NORM = p9core.LEARNING_RATE, p9core.CLIP_NORM
VISIT = p9core.VISIT
BRANCH_SIZE = 256  # T-OQ: N / 256 branches of 256 slots, 2 visited
TREE_CANDIDATES = VISIT * BRANCH_SIZE  # 512
IVF_LIST_TARGET = 256  # F-OQ-IVF: N / 256 centroids
IVF_CANDIDATES = 512
LLOYD_ITERATIONS = 10  # section 5.5 (lead's choice)
SLOT_COUNTS = (4096, 16384, 65536)

# --- arms (section 3) ------------------------------------------------------------------------------------------------
ARMS = ("F-OQ", "T-OQ", "H8", "D-OQ", "R2")  # the trained arms (lane L adds F-LA)
LANE_ARM = "F-LA"
MEMORY_ARMS = ("F-OQ", "T-OQ", "H8", "R2")  # arms with a value table
CLASSIFIED_ARMS = ("F-OQ", "F-OQ-IVF", "T-OQ", "H8")  # arm classes of section 8.4 (F-OQ-IVF is F-OQ's cells read through an index)
EVAL_ONLY_ARMS = ("F-OQ-IVF", "KNN-W", "KNN-W-IVF", "DICT", "NO-MEMORY", "UNSEEN")
LEARNED_KEY_ARMS = ("F-OQ", "F-OQ-IVF", "T-OQ")  # the outcome label requires learned keys (section 8.7)
EFFICIENCY_ARMS = ("F-OQ", "T-OQ")

# --- grid of facts and slots (section 5.1) -------------------------------------------------------------------------------
GRID_CELLS: tuple[tuple[int, int], ...] = ((2048, 4096), (8192, 4096), (8192, 16384), (8192, 65536), (32768, 4096), (32768, 16384), (32768, 65536))
DOQ_CELLS = ((2048, 4096), (8192, 16384), (8192, 65536), (32768, 16384), (32768, 65536))
R2_CELLS = ((2048, 4096), (8192, 16384), (8192, 65536), (32768, 65536))
DIAGONAL = ((2048, 4096), (8192, 16384), (32768, 65536))
FACT_TABLE = 32768
OVERLOAD_FACTS = 65536
LOAD_FACTS_4096 = (8192, 16384, 32768, 65536)  # section 10.1 item 0
LOAD_FACTS_16384 = (8192, 32768, 65536, 131072)
CALIBRATION_TABLE_FACTS = 131072
UNSEEN_FACTS = p9core.UNSEEN_FACTS
LANE_D_STUB = 128  # P9's builder needs a Lane D world; S1 builds the smallest one and never uses it

U_P = 8192  # section 5.4 (lead's choice); not tuned
RUN_MULTIPLIER = {4096: 6, 16384: 4, 65536: 2}  # run lengths 6 / 4 / 2 * U_P
R2_RUN_MULTIPLIER = 1
SNAPSHOT_FRACTIONS = (1 / 16, 1 / 8, 1 / 4, 1 / 2, 1.0, 2.0, 4.0)
MC_GRID = (1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 6.0)  # section 5.4
OVERLOAD_U_P_CANDIDATES = (8192, 16384, 32768)  # section 10.1 item 0, row 4 (lead's choice)
DENSE_RATES = (0.001, 0.003, 0.01)  # section 10.1 item 3 (lead's choice)
DENSE_TIE_DIFFERENCE = 0.02
DOQ_INIT_BOUND_FANIN = 0.25  # w1, b1 ~ U(-1/4, 1/4); w2 ~ U(-1/sqrt(h), 1/sqrt(h))
DOQ_PARAMETER_TOLERANCE = 0.001  # G8: within 0.1%
SEED_BLOCK_EXTRA = 2  # F-OQ at two extra initialization seeds per seed-block draw

# --- thresholds (sections 7, 8) ---------------------------------------------------------------------------------------------
G2_TESTS = 40  # G2: 40 exact binomial tests at level 1 - 0.001/40
BITS_PER_FACT = p9core.BITS_PER_FACT
REF_R2_MIN = 0.95
DEP_USE_FLOOR = 0.25  # DEP applies to cells with a_use >= 0.25
DEP_USE_OF_RAW = 0.95
GAIN_MIN = 0.5  # bits per fact (lead's choice)
NULL_MAX = 0.25
PLATEAU_MAX = 0.10
LOADED_I_MAX = 4.0
CEILING_I = 4.5
A_USE_FLOOR_CAPACITY = 0.5
ARM_A_USE_AT_LARGEST = 0.80
DENSE_AHEAD_BITS = -0.25
BEATS_DENSE_RATIO = 1.10
TREE_AHEAD_RATIO = 1.03
TREE_COMPETITIVE_RATIO = 0.97
CONVENTIONAL_WITHIN = 0.25
STUDY_B_A_USE = 0.85
STUDY_B_RATIO = 3.0
NOT_ASSESSED_A_USE = 0.5
SUBLINEAR_FACTOR = 2.0
INDEXED_TREE_RATIO = 0.97  # H21-6
HELDOUT_FRAGILE = 0.90
SUPPORT_SAMPLE = 2048
EFFICIENCY_I_T = 3.0
EFFICIENCY_UPDATES_FACTOR = 0.5
EFFICIENCY_COST_FACTOR = 0.8
OPTIMIZER_ASSISTED_RATIO = 1.5
DENSE_FASTER_COST = 0.8
MC_MISMATCH = 1.25
ROBUSTNESS_DROPOUT = (0.05, 0.20)
ROBUSTNESS_NOISE = (0.1, 0.5)
ROBUSTNESS_MASKS = 3
ROBUSTNESS_RISE = 0.05
PAIRED_ALL = 5
PAIRED_MOST = 4
REPLICATES = 5
THROUGHPUT_BATCHES = (1, 128)
THROUGHPUT_REPEATS = 5
THROUGHPUT_CV_MAX = 0.05
LOAD_AVERAGE_MAX = 1.0
TIMING_RETRIES = 3
TIMING_WARMUP_UPDATES = 32
TIMING_UPDATES = 256
TIMING_REPEATS = 3
REHEARSAL_UPDATES = 64

# --- resources and budget (section 10.3) --------------------------------------------------------------------------------------
RSS_WORKER_BYTES = 3 * 1024**3
RSS_AGGREGATE_BYTES = 18 * 1024**3
WORKERS = 6
CAP_HOURS_DEFAULT = 16.0  # the human lead's figure as relayed by the coordinator (raised from 12; ADR-0021 section 15 on the design branch); the cap actually used is the value in the config (resources.cap_hours)
HEADROOM = 2.0
PEAK_PER_WORKER_FOR_HEADROOM = RSS_AGGREGATE_BYTES / (WORKERS * HEADROOM)  # 1.5 GiB

# --- row names, steps, transitions (section 5.1) ---------------------------------------------------------------------------------
_UNIT = {1024: "K"}


def size_name(n: int) -> str:
    """``2048`` -> ``2K``, ``65536`` -> ``64K`` (K = 1,024)."""
    return f"{n // 1024}K" if n % 1024 == 0 else str(n)


def cell_name(facts: int, slots: int) -> str:
    """``8K/16K`` means 8,192 facts in 16,384 slots."""
    return f"{size_name(facts)}/{size_name(slots)}"


class Step(NamedTuple):
    name: str
    facts: int
    small: int  # slots of the smaller cell
    large: int  # slots of the larger cell (four times)

    @property
    def transition(self) -> str:
        return f"{size_name(self.small)}→{size_name(self.large)}"

    @property
    def cells(self) -> tuple[tuple[int, int], tuple[int, int]]:
        return (self.facts, self.small), (self.facts, self.large)


A1, A2 = Step("A1", 8192, 4096, 16384), Step("A2", 8192, 16384, 65536)
B1, B2 = Step("B1", 32768, 4096, 16384), Step("B2", 32768, 16384, 65536)
B3 = Step("B3", OVERLOAD_FACTS, 16384, 65536)  # the overload row's step (section 10.1 item 0, row 4)
TRANSITIONS = ("4K→16K", "16K→64K")
DIAGONAL_STEPS = (("2K/4K", "8K/16K"), ("8K/16K", "32K/64K"))  # Study B diagonal steps; their off-diagonal steps are A1 and B2


# --- the plan: the part of the freeze record that changes the registry (section 8 opening, 10.3) --------------------------------------
@dataclass(frozen=True)
class Plan:
    """What the freeze may change: the overload row (its own U_P), the draws that carry the seed block (cuts 1 and 2 remove them), the D-OQ cells cut by
    cut 3, and lane L. Nothing else is a registry option."""

    overload_u_p: int | None = None
    seed_block_draws: tuple[int, ...] = (1,)
    dense_cut: tuple[str, ...] = ()
    lane_l: bool = False
    unit: int = 8192  # U_P of the rows (8,192; only the DRY stage and unit tests use another, a multiple of 4)

    def __post_init__(self) -> None:
        if self.unit != U_P and (self.unit <= 0 or self.unit % 4):
            raise ValueError("a non-registered unit must be a positive multiple of 4")
        if self.overload_u_p is not None and self.overload_u_p not in overload_candidates(self.unit):
            raise ValueError(f"the overload row's U_P is one of {overload_candidates(self.unit)}")
        if any(d not in (1, 2) for d in self.seed_block_draws) or len(set(self.seed_block_draws)) != len(self.seed_block_draws):
            raise ValueError("the seed block is on draw 1 and/or draw 2")
        if 2 in self.seed_block_draws and 1 not in self.seed_block_draws:
            raise ValueError("cut 1 removes draw 2 before draw 1 (section 10.3)")
        if any(c not in DOQ_CUTTABLE for c in self.dense_cut) or len(set(self.dense_cut)) != len(self.dense_cut):
            raise ValueError(f"cut 3 may remove D-OQ at {DOQ_CUTTABLE} only")

    @property
    def table_facts(self) -> int:
        return OVERLOAD_FACTS if self.overload_u_p is not None else FACT_TABLE

    @property
    def steps(self) -> tuple[Step, ...]:
        return (A1, A2, B1, B3) if self.overload_u_p is not None else (A1, A2, B1, B2)

    def key(self) -> str:
        parts = [f"overload={self.overload_u_p}", "seedblock=" + (",".join(map(str, self.seed_block_draws)) or "none"), "doqcut=" + (",".join(self.dense_cut) or "none"), f"lane={int(self.lane_l)}"]
        if self.unit != U_P:
            parts.append(f"unit={self.unit}")
        return "|".join(parts)

    def as_json(self) -> dict[str, Any]:
        return {"overload_u_p": self.overload_u_p, "seed_block_draws": list(self.seed_block_draws), "dense_cut": list(self.dense_cut), "lane_l": self.lane_l, "unit": self.unit}

    @classmethod
    def from_json(cls, data: Mapping[str, Any]) -> "Plan":
        return cls(None if data["overload_u_p"] is None else int(data["overload_u_p"]), tuple(int(d) for d in data["seed_block_draws"]), tuple(data["dense_cut"]), bool(data["lane_l"]), int(data.get("unit", U_P)))


DOQ_CUTTABLE = ("8K/64K", "32K/16K")  # cut 3: only the larger cell of a step whose smaller cell was predicted not loaded; 8K/64K is cut first (section 10.3)


def overload_candidates(unit: int = U_P) -> tuple[int, ...]:
    """The overload row's candidate U_P values (section 10.1 item 0): 1, 2 and 4 times U_P."""
    return tuple(unit * k for k in (1, 2, 4))


def plan_configurations(overload_u_p: int | None = None, unit: int = U_P) -> list[Plan]:
    """Every registry the freeze can select (lane L is never enabled by this code): three seed-block choices x four D-OQ cut sets, with or without the overload row of a given U_P
    (the caps table has one entry each)."""
    out = []
    for blocks in ((1, 2), (1,), ()):
        for cuts in ((), ("8K/64K",), ("32K/16K",), ("8K/64K", "32K/16K")):
            out.append(Plan(overload_u_p, blocks, cuts, False, unit))
    return out


# --- cells ------------------------------------------------------------------------------------------------------------------
KINDS = ("P", "SB", "CAL", "LN")  # registered, seed block, calibration, lane L


@dataclass(frozen=True)
class Cell:
    """One trained cell. ``draw`` is the data draw (registered: the replicate; calibration: 1 or 2); ``u_p`` the row's U_P (8,192 unless the overload row);
    ``run_updates`` the registered run length. ``init_seed`` is the initialization seed of this run."""

    kind: str
    arm: str
    facts: int
    slots: int
    draw: int
    init_seed: int
    u_p: int
    run_updates: int
    lr: float
    test: bool = False
    label: str = field(default="", compare=False)

    def __post_init__(self) -> None:
        if self.kind not in KINDS or self.arm not in (*ARMS, LANE_ARM) or self.slots <= 0 or self.facts <= 0 or self.run_updates <= 0 or self.u_p <= 0:
            raise ValueError(f"unregistered P10S1 cell: {self.label or (self.kind, self.arm, self.facts, self.slots)}")
        if self.arm == "R2" and self.facts > self.slots:
            raise ValueError("R2 is defined only where facts <= slots (section 3)")

    @property
    def name(self) -> str:
        return cell_name(self.facts, self.slots)

    @property
    def replicate(self) -> int:
        return self.draw

    @property
    def load(self) -> float:
        return self.facts / self.slots


def run_length(arm: str, slots: int, u_p: int = U_P) -> int:
    """Registered run length (section 5.4): 6 / 4 / 2 * U_P at 4,096 / 16,384 / 65,536 slots; R2 runs U_P."""
    return (R2_RUN_MULTIPLIER if arm == "R2" else RUN_MULTIPLIER[slots]) * u_p


def _fmt(x: float) -> str:
    return f"{x:g}"


def make_label(kind: str, arm: str, facts: int, slots: int, draw: int, init_seed: int, u_p: int, run_updates: int, lr: float, test: bool = False) -> str:
    """Label of a cell. Underscore-separated so that arm names keep their hyphens; ``u`` and ``y`` (run length) are written when they differ from the
    registered defaults, ``i`` when the initialization seed is not the replicate's, ``lr`` when it is not 0.003."""
    tokens = [kind, arm, f"f{facts}", f"n{slots}", f"d{draw}", f"i{init_seed}"]
    if u_p != U_P:
        tokens.append(f"u{u_p}")
    if run_updates != run_length(arm, slots, u_p):
        tokens.append(f"y{run_updates}")
    if lr != LEARNING_RATE:
        tokens.append(f"lr{_fmt(lr)}")
    return ("TEST_" if test else "") + "_".join(tokens)


def make_cell(kind: str, arm: str, facts: int, slots: int, draw: int, init_seed: int, *, u_p: int = U_P, run_updates: int | None = None, lr: float = LEARNING_RATE, test: bool = False) -> Cell:
    y = run_length(arm, slots, u_p) if run_updates is None else run_updates
    return Cell(kind, arm, facts, slots, draw, init_seed, u_p, y, lr, test, make_label(kind, arm, facts, slots, draw, init_seed, u_p, y, lr, test))


def parse_label(label: str) -> Cell:
    """The cell named by ``label`` (``ValueError`` otherwise); stateless, so registry membership is checked separately (``registered_cells``)."""
    tokens = label.split("_")
    test = tokens[0] == "TEST"
    if test:
        tokens = tokens[1:]
    try:
        kind, arm, f, n, d, i = tokens[:6]
        extra = {t[0] if t[0] in "uy" else "lr": t for t in tokens[6:]}
        u_p = int(extra["u"][1:]) if "u" in extra else U_P
        lr = float(extra["lr"][2:]) if "lr" in extra else LEARNING_RATE
        if not (f[0] == "f" and n[0] == "n" and d[0] == "d" and i[0] == "i"):
            raise ValueError(label)
        facts, slots, draw, init = int(f[1:]), int(n[1:]), int(d[1:]), int(i[1:])
        y = int(extra["y"][1:]) if "y" in extra else run_length(arm, slots, u_p)
        cell = make_cell(kind, arm, facts, slots, draw, init, u_p=u_p, run_updates=y, lr=lr, test=test)
    except (ValueError, KeyError, IndexError) as exc:
        raise ValueError(f"unknown P10S1 cell label {label!r}") from exc
    if cell.label != label:
        raise ValueError(f"unknown P10S1 cell label {label!r}")
    return cell


def labels_of(items: Iterable[Cell]) -> list[str]:
    return [c.label for c in items]


def init_seed_of(replicate: int) -> int:
    """Replicate r is data draw r with initialization seed 2100 + r (section 6.2)."""
    if not 1 <= replicate <= REPLICATES:
        raise ValueError("replicates are 1..5")
    return 2100 + replicate


INIT_SEEDS = tuple(init_seed_of(r) for r in range(1, REPLICATES + 1))
SEED_BLOCK_INITS: dict[tuple[int, int], int] = {(1, 1): 2111, (2, 1): 2121, (1, 2): 2112, (2, 2): 2122}  # (extra index, draw) -> seed: 21<extra><draw>
CALIBRATION_INIT_SEED = 2191
REHEARSAL_INIT_SEED = 2192
CALIBRATION_INIT_SEEDS = (CALIBRATION_INIT_SEED, REHEARSAL_INIT_SEED)


def grid_cells(plan: Plan) -> tuple[tuple[int, int], ...]:
    """The grid cells (facts, slots) of a plan: the seven cells and the overload row's two."""
    if plan.overload_u_p is None:
        return GRID_CELLS
    return (*GRID_CELLS, (OVERLOAD_FACTS, 16384), (OVERLOAD_FACTS, 65536))


def u_p_of(plan: Plan, facts: int) -> int:
    return plan.overload_u_p if (plan.overload_u_p is not None and facts == OVERLOAD_FACTS) else plan.unit


def arm_cells(plan: Plan, arm: str) -> tuple[tuple[int, int], ...]:
    """Cells of ``arm`` in a plan (section 6.1): F-OQ, T-OQ, H8 at every cell; D-OQ at the larger cell of every step and every diagonal cell; R2 where facts <= slots."""
    if arm in ("F-OQ", "T-OQ", "H8"):
        return grid_cells(plan)
    if arm == "D-OQ":
        cells = list(DOQ_CELLS)
        if plan.overload_u_p is not None:
            cells.append((OVERLOAD_FACTS, 65536))
        return tuple(c for c in cells if cell_name(*c) not in plan.dense_cut)
    if arm == "R2":
        cells = list(R2_CELLS)
        if plan.overload_u_p is not None:
            cells.append((OVERLOAD_FACTS, 65536))
        return tuple(cells)
    raise ValueError(f"no registered cells for arm {arm!r}")


def registered_cells(plan: Plan | None = None, *, dense_rates: Mapping[int, float] | None = None) -> list[Cell]:
    """The registered cells of a plan: per replicate every arm at its cells (30 configurations, 150 cells by default), plus the seed block (F-OQ x cells x 2
    extra seeds on draw 1 and/or 2) and, when the freeze enables it, lane L (15 cells). ``dense_rates`` maps a slot count to D-OQ's calibrated learning rate."""
    plan = plan or Plan()
    rates = dict(dense_rates or {})
    out: list[Cell] = []
    for r in range(1, REPLICATES + 1):
        for arm in ARMS:
            for facts, slots in arm_cells(plan, arm):
                lr = rates.get(slots, LEARNING_RATE) if arm == "D-OQ" else LEARNING_RATE
                out.append(make_cell("P", arm, facts, slots, r, init_seed_of(r), u_p=u_p_of(plan, facts), lr=lr))
    for draw in plan.seed_block_draws:
        for k in range(1, SEED_BLOCK_EXTRA + 1):
            for facts, slots in GRID_CELLS:  # the seed block is seven cells (section 6.1; ruling m2), also with the overload row
                out.append(make_cell("SB", "F-OQ", facts, slots, draw, SEED_BLOCK_INITS[(k, draw)], u_p=u_p_of(plan, facts)))
    if plan.lane_l:
        out.extend(lane_cells())
    return out


LANE_CELLS = ((2048, 4096), (8192, 4096), (8192, 16384))


def lane_cells() -> list[Cell]:
    """Lane L (section 5.6): F-LA at 2K/4K, 8K/4K and 8K/16K, five replicates, 4 * F updates each (8,192 at 2K/4K; 32,768 at the other two). The lane is off unless the freeze
    record enables it, and F-LA (S0's frozen candidate) has no implementation in this tree."""
    return [make_cell("LN", LANE_ARM, f, n, r, init_seed_of(r), run_updates=4 * f) for r in range(1, REPLICATES + 1) for f, n in LANE_CELLS]


CONFIGURATIONS_PER_REPLICATE = 30
REGISTERED_CELL_COUNT = 150


def _assert_registry() -> None:
    cells = registered_cells(Plan(seed_block_draws=()))
    if len(cells) != REGISTERED_CELL_COUNT or sum(1 for c in cells if c.draw == 1) != CONFIGURATIONS_PER_REPLICATE:
        raise ImportError("P10S1 registry counts differ from section 6.1 (30 configurations, 150 cells)")
    if len(registered_cells(Plan(seed_block_draws=(1,)))) != 164 or len(registered_cells(Plan(seed_block_draws=(1, 2)))) != 178 or len(lane_cells()) != 15:
        raise ImportError("P10S1 seed block or lane L counts differ from sections 5.6 and 6.1")
    labels = labels_of(registered_cells(Plan(seed_block_draws=(1, 2), lane_l=True)))
    if len(set(labels)) != len(labels):
        raise ImportError("P10S1 cell labels are not unique")


_assert_registry()


# --- calibration cells (section 10.1) -----------------------------------------------------------------------------------------------
CALIBRATION_DRAWS = (1, 2)
LOAD_CALIBRATION_UPDATES = 65536  # 8 U_P


def load_updates(unit: int = U_P) -> int:
    return 8 * unit  # 65,536 = 8 U_P


def load_calibration_cells(unit: int = U_P) -> list[Cell]:
    """Item 0: F-OQ at 4,096 slots with 8,192 / 16,384 / 32,768 / 65,536 facts and at 16,384 slots with 8,192 / 32,768 / 65,536 / 131,072 facts, on both calibration
    draws, to 65,536 updates (8 U_P): 16 runs."""
    out = []
    for slots, loads in ((4096, LOAD_FACTS_4096), (16384, LOAD_FACTS_16384)):
        for facts in loads:
            for d in CALIBRATION_DRAWS:
                out.append(make_cell("CAL", "F-OQ", facts, slots, d, CALIBRATION_INIT_SEED, u_p=unit, run_updates=load_updates(unit)))
    return out


def u_p_check_cells(unit: int = U_P) -> list[Cell]:
    """Item 1: R2 and F-OQ on the three diagonal cells to U_P = 8,192: 12 runs."""
    return [make_cell("CAL", arm, f, n, d, CALIBRATION_INIT_SEED, u_p=unit, run_updates=unit) for arm in ("R2", "F-OQ") for f, n in DIAGONAL for d in CALIBRATION_DRAWS]


def h8_report_cells(unit: int = U_P) -> list[Cell]:
    """Item 2: H8 on the diagonal cells to U_P: 6 runs (reported, gates nothing)."""
    return [make_cell("CAL", "H8", f, n, d, CALIBRATION_INIT_SEED, u_p=unit, run_updates=unit) for f, n in DIAGONAL for d in CALIBRATION_DRAWS]


def dense_rate_cells(unit: int = U_P) -> list[Cell]:
    """Item 3: D-OQ at 8K/16K and 32K/64K at the three rates on both draws to the run length of its slot count: 12 runs."""
    return [make_cell("CAL", "D-OQ", f, n, d, CALIBRATION_INIT_SEED, u_p=unit, run_updates=run_length("D-OQ", n, unit), lr=lr) for (f, n) in ((8192, 16384), (32768, 65536)) for lr in DENSE_RATES for d in CALIBRATION_DRAWS]


def overload_u_p_cells(unit: int = U_P) -> list[Cell]:
    """Item 0, row 4 only: F-OQ and R2 at 65,536 facts in 65,536 slots on both draws, to the largest candidate U_P (read at the three candidates): 4 runs."""
    return [make_cell("CAL", arm, OVERLOAD_FACTS, 65536, d, CALIBRATION_INIT_SEED, u_p=unit, run_updates=max(overload_candidates(unit))) for arm in ("F-OQ", "R2") for d in CALIBRATION_DRAWS]


def calibration_cells(include_overload: bool = False, unit: int = U_P) -> list[Cell]:
    """The calibration (46 runs; 50 with the overload row's U_P calibration)."""
    cells = [*load_calibration_cells(unit), *u_p_check_cells(unit), *h8_report_cells(unit), *dense_rate_cells(unit)]
    return cells + (overload_u_p_cells(unit) if include_overload else [])


CALIBRATION_RUNS, CALIBRATION_RUNS_WITH_OVERLOAD = 46, 50


def load_snapshots(slots: int, updates: int | None = None, unit: int = U_P) -> tuple[int, ...]:
    """Load calibration snapshots: the doubling grid (U_P/16 x 2^k: 512, 1,024, ... 65,536) and the registered U_run/2 and U_run of the slot count (24,576 and 49,152 at 4,096
    slots; 16,384 and 32,768 at 16,384 slots)."""
    top = load_updates(unit) if updates is None else updates
    grid = {unit * 2**k // 16 for k in range(0, 8) if (unit * 2**k) % 16 == 0}
    run = run_length("F-OQ", slots, unit)
    return tuple(sorted(s for s in {*grid, run // 2, run} if 1 <= s <= top))


def _check_calibration_counts() -> None:
    if len(calibration_cells()) != CALIBRATION_RUNS or len(calibration_cells(True)) != CALIBRATION_RUNS_WITH_OVERLOAD or len(load_calibration_cells()) != 16:
        raise ImportError("P10S1 calibration counts differ from section 10.1 (46 runs, +4)")
    if len(u_p_check_cells()) != 12 or len(h8_report_cells()) != 6 or len(dense_rate_cells()) != 12:
        raise ImportError("P10S1 calibration item counts differ from section 10.1")
    labels = labels_of(calibration_cells(True))
    if len(set(labels)) != len(labels):
        raise ImportError("P10S1 calibration labels are not unique")


_check_calibration_counts()


# --- snapshots, exposures (sections 5.4, 7.1) -------------------------------------------------------------------------------------------
def multiple_of(u_p: int, m: float) -> int:
    value = u_p * m
    if value != int(value):
        raise ValueError(f"{m} x U_P = {value} is not an integer number of updates")
    return int(value)


def snapshot_updates(u_p: int, run_updates: int, mc: Iterable[int] = ()) -> tuple[int, ...]:
    """Snapshots of a cell (section 5.4): U_P x {1/16, 1/8, 1/4, 1/2, 1, 2, 4} up to the run length, U_run / 2, U_run, and every matched-compute snapshot
    (``mc``: ``m x U_P`` of the MC grid, at most the run length). Integers; a snapshot below 1 is dropped."""
    marks = {int(u_p * f) for f in SNAPSHOT_FRACTIONS if u_p * f == int(u_p * f) and 1 <= u_p * f <= run_updates}
    marks.update({run_updates // 2, run_updates})
    marks.update(int(m) for m in mc if 1 <= m <= run_updates)
    return tuple(sorted(m for m in marks if m >= 1))


def exposures_per_fact(updates: int, facts: int) -> float:
    """Analytical answer-site exposures per fact (128 per update)."""
    return updates * ANSWER_SITES_PER_BATCH / facts


def me_updates(facts: int, u_p: int = U_P) -> int:
    """ME readout across rows (section 5.4): 128 * U_P / 32,768 exposures per fact; 8,192 facts at U_P/4, 2,048 facts at U_P/16."""
    return u_p * facts // FACT_TABLE


def snapshot_stem(update: int) -> str:
    return f"u{update:07d}"


# --- information of a count (section 7.1) -------------------------------------------------------------------------------------------------
@functools.cache
def chance_interval(n: int) -> p9core.ChanceInterval:
    """G2's exact binomial interval at level 1 - 0.001/40 around 1/32 ([34, 100], [192, 325], [894, 1,159] at 2,048, 8,192, 32,768 facts)."""
    return p9core.chance_interval(n, G2_TESTS)


def at_chance(correct: int, n: int) -> bool:
    """Inside the G2 interval: what every rule means by "chance" (an empty set is at chance)."""
    if n <= 0:
        return True
    iv = chance_interval(n)
    return iv.low <= correct <= iv.high


def bits_per_fact(a_use_count: int, n: int) -> float:
    """i = 5 - h2(e) - e log2 31 bits per fact with e = 1 - a_use, set to 0 when the count is at or below the upper end of the chance interval (G2)."""
    if n <= 0:
        return 0.0
    if not 0 <= a_use_count <= n:
        raise ValueError("the count must lie in [0, n]")
    if a_use_count <= chance_interval(n).high:
        return 0.0
    return float(p9core.fano_bits_per_fact(a_use_count / n))


def i_to_a_use(i: float) -> float:
    """The a_use whose i is ``i`` (bisection; ADR checkpoints: 1.523 -> 0.5, 3.287 -> 0.8, 4.036 -> 0.9, 4.466 -> 0.95)."""
    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if p9core.fano_bits_per_fact(mid) < i:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


# --- D-OQ width (section 5.3) ----------------------------------------------------------------------------------------------------------------
def foq_trainable_parameters(slots: int) -> int:
    """F-OQ: keys [N, 16], values [N, 32], wo [32, 32], gate: 48 N + 1,025 (no query projection: the query is a fixed code)."""
    return slots * (KEY_WIDTH + HIDDEN_WIDTH) + HIDDEN_WIDTH * HIDDEN_WIDTH + 1


def doq_hidden(slots: int) -> int:
    """h such that 49 h + 1 equals F-OQ's parameter count within 0.1% (w1 [h, 16], b1 [h], w2 [32, h], gate): the nearest integer to (P - 1) / 49."""
    return int(round((foq_trainable_parameters(slots) - 1) / (KEY_WIDTH + 1 + HIDDEN_WIDTH)))


def doq_trainable_parameters(hidden: int) -> int:
    return (KEY_WIDTH + 1 + HIDDEN_WIDTH) * hidden + 1


# --- work per query (section 7.4; the formulas the counters must equal, gate G7) ---------------------------------------------------------------------
def work_formula(arm: str, slots: int, *, hidden: int | None = None, candidates: int | None = None) -> dict[str, int]:
    """Key scores K (each 16 wide), value rows V and W = 16 K + 32 V + 1,024 per query. F-OQ: K = N, V = 8. T-OQ: K = N/256 + 512, V = 8. H8: K = 0, V = 8.
    R2: K = 0, V = 1. D-OQ: W = 48 h plus h bias additions (K and V are not defined; ``hidden`` is h). F-OQ-IVF: K = N/256 + ``candidates`` (measured)."""
    if arm == "D-OQ":
        h = doq_hidden(slots) if hidden is None else hidden
        return {"K": 0, "V": 0, "hidden": h, "W": 48 * h, "bias_additions": h}
    if arm == "F-OQ":
        k, v = slots, TOP
    elif arm == "T-OQ":
        k, v = slots // BRANCH_SIZE + TREE_CANDIDATES, TOP
    elif arm == "H8":
        k, v = 0, TOP
    elif arm == "R2":
        k, v = 0, 1
    elif arm == "F-OQ-IVF":
        if candidates is None:
            raise ValueError("F-OQ-IVF's work is measured: pass the candidate count")
        k, v = slots // IVF_LIST_TARGET + candidates, TOP
    else:
        raise ValueError(f"no work formula for {arm!r}")
    return {"K": k, "V": v, "W": KEY_WIDTH * k + HIDDEN_WIDTH * v + HIDDEN_WIDTH * HIDDEN_WIDTH}


# --- seeds and gate G9 (section 6.3) -------------------------------------------------------------------------------------------------------------------
REGISTERED_BASE = 210001
DRAW_STRIDE = 100
CALIBRATION_BASES = (219001, 219101)
REHEARSAL_BASE = 219201
TEST_SEED_BASE, TEST_SEED_TOP = 921001, 921999
H8_OFFSET, MASK_OFFSETS, INDEX_OFFSET = 40, tuple(range(50, 60)), 60
SUPPORT_SAMPLE_OFFSET = 58  # the seeded sample of facts for the minimal supports (inside the 50..59 block)
DERIVED_INIT_OFFSETS = (1000, 2000, 3000, 4000, 5000)  # ``_matrix``'s seed + 1000 k (keys, values, wq, wo, router); D-OQ draws w1, b1, w2 from the same set
SEED_RANGE = (210001, 219999)  # the study's data seeds all lie inside this range


def seed_set(name: str, base: int) -> p9core.SeedSet:
    """Layout inside a set: base + 0..13 the fourteen data seeds in P9's order, null seeds at base + 20..22 and base + 30..32 (section 6.3)."""
    values = {n: base + i for i, n in enumerate(p9core.DATA_SEEDS)}
    return p9core.SeedSet(name, **values, null_seeds_a=tuple(base + 20 + i for i in range(3)), null_seeds_b=tuple(base + 30 + i for i in range(3)))


def draw_base(replicate: int) -> int:
    if not 1 <= replicate <= REPLICATES:
        raise ValueError("registered draws are 1..5")
    return REGISTERED_BASE + DRAW_STRIDE * (replicate - 1)


def registered_draw_seeds(replicate: int) -> p9core.SeedSet:
    """``p10s1-draw-<r>``, bases 210001, 210101, 210201, 210301, 210401."""
    return seed_set(f"p10s1-draw-{replicate}", draw_base(replicate))


def calibration_seeds(draw: int) -> p9core.SeedSet:
    """``p10s1-cal-<k>``, bases 219001 and 219101."""
    if draw not in CALIBRATION_DRAWS:
        raise ValueError("calibration draws are 1 and 2")
    return seed_set(f"p10s1-cal-{draw}", CALIBRATION_BASES[draw - 1])


def rehearsal_seeds() -> p9core.SeedSet:
    return seed_set("p10s1-rehearsal", REHEARSAL_BASE)


def test_seeds(offset: int = 0) -> p9core.SeedSet:
    """Unit tests and the DRY stage: 921001 up to 921999 (offsets 0 to 8)."""
    base = TEST_SEED_BASE + 100 * offset
    if offset < 0 or base + 99 > TEST_SEED_TOP:
        raise ValueError("test seed offset out of range (0..8)")
    return seed_set(f"p10s1-test-{offset}", base)


def h8_seed(seeds: p9core.SeedSet) -> int:
    return seeds.facts + H8_OFFSET


def mask_seed(seeds: p9core.SeedSet, k: int) -> int:
    """Derangement and mask seeds: base + 50 .. base + 59."""
    if not 0 <= k < len(MASK_OFFSETS):
        raise ValueError("mask index 0..9")
    return seeds.facts + MASK_OFFSETS[k]


def index_seed(seeds: p9core.SeedSet) -> int:
    return seeds.facts + INDEX_OFFSET


def set_values(s: p9core.SeedSet) -> frozenset[int]:
    """Every integer a seed set uses: data and null seeds, the H8 hash seed, the ten derangement and mask seeds and the index seed."""
    b = s.facts
    return frozenset([*s.data_values(), *s.null_seeds_a, *s.null_seeds_b, b + H8_OFFSET, *(b + o for o in MASK_OFFSETS), b + INDEX_OFFSET])


def derived_inits(inits: Iterable[int]) -> frozenset[int]:
    return frozenset(i + k for i in inits for k in DERIVED_INIT_OFFSETS)


# the other studies' seeds named by the ADR (section 6.3), as inclusive ranges and single seeds
OTHER_STUDY_RANGES: dict[str, tuple[tuple[int, int], ...]] = {
    "P9": ((170001, 171343), (179001, 179933), (1701, 1702)),
    "P9-I": ((182001, 182020), (180101, 181900), (1791, 1792), (1801, 1802), (900001, 900233)),
    "review diagnostics": ((500001, 500004), (941001, 941001)),
    "P9-II": ((190001, 191599), (1891, 1892), (1901, 1902), (910001, 919999)),
    "S0 (ADR-0020)": ((200001, 209999), (2001, 2002), (2091, 2092), (920001, 920999)),
    "S2 (ADR-0022)": ((220001, 228999), (229001, 229999)),
}


def _in_ranges(v: int, ranges: Sequence[tuple[int, int]]) -> bool:
    return any(lo <= v <= hi for lo, hi in ranges)


def legacy_config_seeds(root: Path | None = None) -> frozenset[int]:
    """The seeds of P1 to P8 read from their configs: every integer under a key whose name contains ``seed`` (``configs/*.toml`` except the P9, P10 configs)."""
    base = root or repo_root()
    found: set[int] = set()

    def walk(value: Any, key: str) -> None:
        if isinstance(value, dict):
            for k, v in value.items():
                walk(v, k)
        elif isinstance(value, list):
            for v in value:
                walk(v, key)
        elif isinstance(value, int) and not isinstance(value, bool) and "seed" in key.lower() and "offset" not in key.lower():
            found.add(int(value))

    for path in sorted((base / "configs").glob("*.toml")):
        if path.name.startswith(("p9", "p10")):
            continue
        with path.open("rb") as stream:
            walk(tomllib.load(stream), "")
    return frozenset(found)


def seed_namespaces() -> dict[str, frozenset[int]]:
    """S1's declared seeds by name, the seeds its generators derive (initialization seed + 1000 k) and the test range."""
    registered = frozenset().union(*(set_values(registered_draw_seeds(r)) for r in range(1, REPLICATES + 1)))
    calibration = frozenset().union(*(set_values(calibration_seeds(d)) for d in CALIBRATION_DRAWS))
    inits = frozenset([*INIT_SEEDS, *SEED_BLOCK_INITS.values(), *CALIBRATION_INIT_SEEDS])
    return {
        "registered": registered,
        "calibration": calibration,
        "rehearsal": set_values(rehearsal_seeds()),
        "init": inits,
        "derived_init": derived_inits(inits),
        "test": frozenset(range(TEST_SEED_BASE, TEST_SEED_TOP + 1)),
    }


def seed_check(root: Path | None = None, namespaces: Mapping[str, frozenset[int]] | None = None) -> dict[str, Any]:
    """Gate G9: S1's declared seeds and the seeds its generators derive are disjoint from each other and from the listed seeds of P9, P9-I, the review diagnostics,
    P9-II, S0, S2 and the seeds of P1-P8 read from their configs (and from those studies' own derived initialization seeds). Returns ``passed`` and every overlap."""
    ns = dict(namespaces or seed_namespaces())
    overlaps: list[str] = []
    names = sorted(ns)
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            common = ns[a] & ns[b]
            if common:
                overlaps.append(f"{a} and {b}: {sorted(common)[:5]}")
    other_inits = {1701, 1702, 1791, 1792, 1801, 1802, 1891, 1892, 1901, 1902, 2001, 2002, 2091, 2092}
    other_derived = derived_inits(other_inits)
    legacy = legacy_config_seeds(root)
    for name, values in ns.items():
        for study, ranges in OTHER_STUDY_RANGES.items():
            hit = sorted(v for v in values if _in_ranges(v, ranges))
            if hit:
                overlaps.append(f"{name} and {study}: {hit[:5]}")
        for label, seeds in (("P1-P8 configs", legacy), ("other studies' derived initialization seeds", other_derived), ("other studies' initialization seeds", frozenset(other_inits))):
            hit = sorted(values & seeds)
            if hit:
                overlaps.append(f"{name} and {label}: {hit[:5]}")
    for name in ("registered", "calibration", "rehearsal"):
        outside = sorted(v for v in ns[name] if not SEED_RANGE[0] <= v <= SEED_RANGE[1])
        if outside:
            overlaps.append(f"{name} has seeds outside {SEED_RANGE}: {outside[:5]}")
    return {
        "passed": not overlaps, "overlaps": overlaps, "namespaces": {k: len(v) for k, v in ns.items()}, "legacy_config_seeds": len(legacy),
        "scope_note": "P1-P8 seeds are read from configs only; seeds written in code (for example src/arborlm/p7a_core.py) are not scanned here (the audit's literal scan found no overlap)",
    }


def assert_namespaces_disjoint() -> None:
    result = seed_check()
    if not result["passed"]:
        raise ValueError("P10S1 seed namespaces overlap: " + "; ".join(result["overlaps"][:5]))


assert_namespaces_disjoint()

SEED_MODES = ("registered", "calibration", "rehearsal")


TEST_SWITCH_ENV = "P10S1_TEST_SEEDS"


def test_switch() -> bool:
    """The test-only switch (environment variable ``P10S1_TEST_SEEDS=1``, ADR-0021 section 22 M8): the registered driver then runs ONLY on the unit-test seed sets ``p10s1-test-0`` to
    ``-4`` (never on a registered draw), with the synthetic backbone and the DRY sizes, so that the whole registered sequence can be exercised end to end before the freeze. With
    the switch off, only ``p10s1-draw-1..5`` are accepted in registered mode; the two sets of seeds are never mixed."""
    return os.environ.get(TEST_SWITCH_ENV) == "1"


def check_seed_set(mode: str, seed_set_name: str) -> None:
    """``registered``: only ``p10s1-draw-1..5``; ``calibration``: only ``p10s1-cal-1`` and ``-2``; ``rehearsal``: only ``p10s1-rehearsal``; unit tests and the DRY
    stage use ``p10s1-test-k`` in the calibration or rehearsal modes. Anything else is refused. No registered panel is ever used in calibration or rehearsal."""
    if mode not in SEED_MODES:
        raise ValueError(f"unknown mode {mode!r}")
    if mode == "registered":
        ok = bool(re.fullmatch(r"p10s1-test-[0-4]" if test_switch() else r"p10s1-draw-[1-5]", seed_set_name))
    elif mode == "calibration":
        ok = bool(re.fullmatch(r"p10s1-cal-[12]", seed_set_name)) or seed_set_name.startswith("p10s1-test-")
    else:
        ok = seed_set_name == "p10s1-rehearsal" or seed_set_name.startswith("p10s1-test-")
    if not ok:
        raise ValueError(f"mode {mode!r} cannot use the {seed_set_name!r} seed set")


DRAW_NAMES = tuple(f"p10s1-draw-{r}" for r in range(1, REPLICATES + 1))
TEST_DRAW_NAMES = tuple(f"p10s1-test-{r}" for r in range(REPLICATES))


def draw_names() -> tuple[str, ...]:
    """The five registered draws' seed-set names (under the test switch: the five test sets)."""
    return TEST_DRAW_NAMES if test_switch() else DRAW_NAMES


def draw_seeds(replicate: int) -> p9core.SeedSet:
    """The seeds of registered draw ``replicate`` (under the test switch: ``test_seeds(replicate - 1)``)."""
    return test_seeds(replicate - 1) if test_switch() else registered_draw_seeds(replicate)


def seeds_of_name(name: str) -> p9core.SeedSet:
    m = re.fullmatch(r"p10s1-(draw|cal)-(\d+)", name)
    if m is None:
        raise ValueError(f"not a P10S1 seed set name: {name!r}")
    return registered_draw_seeds(int(m[2])) if m[1] == "draw" else calibration_seeds(int(m[2]))


# --- config ---------------------------------------------------------------------------------------------------------------------------------------------
MADDS_FORMULA = (
    "B = 16 contexts, T = 63 positions, Q = 8 B = 128 answer-site queries; one whole training update in multiply-adds. "
    "backbone forward: B (2 (T 32 96 + 4 T T 8 + 4 T T 8 + T 32 32 + 2 T 32 64) + T 32 256). "
    "backbone backward (weights frozen: input gradients through block 1 and the output head only, the two attention products twice): "
    "B (T 32 96 + T 32 32 + 2 T 32 64 + 4 (4 T T 8) + T 32 256). "
    "arm: F-OQ 2 Q N 16 + 3 Q 32 32; T-OQ 2 Q (N/256 16 + 512 16) + 3 Q 32 32; H8 and R2 3 Q 32 32; D-OQ 2 Q 16 h + 3 Q h 32. "
    "plus 4 x trainable parameters for the AdamW update (elementwise). The matmul terms equal torch's FLOP counter / 2 (a test)"
)
GENERATION_DEFAULT = {"cap_seconds": 1800.0, "provisional": True, "table_facts": FACT_TABLE}


def registered_config(cap_hours: float = CAP_HOURS_DEFAULT, generation: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """The configuration mirrored in ``configs/p10s1_capacity.toml``. ``resources.cap_hours`` is the one value the human lead may change; it is read from the config."""
    return {
        "schema_version": SCHEMA,
        "experiment_family": FAMILY,
        "spec_reference": SPEC,
        "memory": {"key_width": KEY_WIDTH, "value_width": HIDDEN_WIDTH, "top": TOP, "temperature": TEMPERATURE, "branch_size": BRANCH_SIZE, "visit": VISIT, "ivf_candidates": IVF_CANDIDATES, "lloyd_iterations": LLOYD_ITERATIONS},
        "training": {"learning_rate": LEARNING_RATE, "clip_norm": CLIP_NORM, "batch_contexts": BATCH_CONTEXTS, "u_p": U_P, "run_multiplier": [RUN_MULTIPLIER[n] for n in SLOT_COUNTS], "r2_run_multiplier": R2_RUN_MULTIPLIER, "loss": "alphabet cross-entropy at answer sites (32 symbols 0x40-0x5F)", "mc_grid": list(MC_GRID), "dense_rates": list(DENSE_RATES)},
        "grid": {"slots": list(SLOT_COUNTS), "cells": [list(c) for c in GRID_CELLS], "doq_cells": [list(c) for c in DOQ_CELLS], "r2_cells": [list(c) for c in R2_CELLS], "overload_facts": OVERLOAD_FACTS, "overload_u_p_candidates": list(OVERLOAD_U_P_CANDIDATES)},
        "replicates": {"count": REPLICATES, "init_base": 2100, "seed_block_inits": [SEED_BLOCK_INITS[k] for k in sorted(SEED_BLOCK_INITS)], "configurations_per_replicate": CONFIGURATIONS_PER_REPLICATE, "registered_cells": REGISTERED_CELL_COUNT},
        "seeds": {"registered_base": REGISTERED_BASE, "draw_stride": DRAW_STRIDE, "calibration_bases": list(CALIBRATION_BASES), "rehearsal_base": REHEARSAL_BASE, "calibration_init": CALIBRATION_INIT_SEED, "rehearsal_init": REHEARSAL_INIT_SEED, "test_base": TEST_SEED_BASE, "test_top": TEST_SEED_TOP, "h8_offset": H8_OFFSET, "index_offset": INDEX_OFFSET},
        "thresholds": {
            "g2_tests": G2_TESTS, "ref_r2_min": REF_R2_MIN, "dep_use_floor": DEP_USE_FLOOR, "dep_use_of_raw": DEP_USE_OF_RAW, "gain_min": GAIN_MIN, "null_max": NULL_MAX, "plateau_max": PLATEAU_MAX,
            "loaded_i_max": LOADED_I_MAX, "ceiling_i": CEILING_I, "a_use_floor_capacity": A_USE_FLOOR_CAPACITY, "arm_a_use_at_largest": ARM_A_USE_AT_LARGEST, "dense_ahead_bits": DENSE_AHEAD_BITS,
            "beats_dense_ratio": BEATS_DENSE_RATIO, "tree_ahead_ratio": TREE_AHEAD_RATIO, "tree_competitive_ratio": TREE_COMPETITIVE_RATIO, "conventional_within": CONVENTIONAL_WITHIN,
            "study_b_a_use": STUDY_B_A_USE, "study_b_ratio": STUDY_B_RATIO, "sublinear_factor": SUBLINEAR_FACTOR, "heldout_fragile": HELDOUT_FRAGILE, "support_sample": SUPPORT_SAMPLE,
            "efficiency_i_t": EFFICIENCY_I_T, "efficiency_updates_factor": EFFICIENCY_UPDATES_FACTOR, "efficiency_cost_factor": EFFICIENCY_COST_FACTOR, "optimizer_assisted_ratio": OPTIMIZER_ASSISTED_RATIO,
            "dense_faster_cost": DENSE_FASTER_COST, "mc_mismatch": MC_MISMATCH, "robustness_rise": ROBUSTNESS_RISE, "paired_all": PAIRED_ALL, "paired_most": PAIRED_MOST,
        },
        "robustness": {"dropout": list(ROBUSTNESS_DROPOUT), "noise": list(ROBUSTNESS_NOISE), "masks": ROBUSTNESS_MASKS},
        "timing": {"warmup_updates": TIMING_WARMUP_UPDATES, "updates": TIMING_UPDATES, "repeats": TIMING_REPEATS, "load_average_max": LOAD_AVERAGE_MAX, "retries": TIMING_RETRIES, "throughput_batches": list(THROUGHPUT_BATCHES), "throughput_repeats": THROUGHPUT_REPEATS, "throughput_cv_max": THROUGHPUT_CV_MAX, "rehearsal_updates": REHEARSAL_UPDATES},
        "cost": {"madds_formula": MADDS_FORMULA},
        "generation": dict(generation or GENERATION_DEFAULT),
        "resources": {"cap_hours": float(cap_hours), "rss_worker_bytes": RSS_WORKER_BYTES, "rss_aggregate_bytes": RSS_AGGREGATE_BYTES, "workers": WORKERS, "headroom": HEADROOM},
    }  # fmt: skip


def validate_config(data: dict[str, Any]) -> dict[str, Any]:
    """Every value equals the module's constants except ``resources.cap_hours``, which may be any positive float (the human lead's figure, read by the ledger)."""
    cap = data.get("resources", {}).get("cap_hours")
    if not isinstance(cap, float) or isinstance(cap, bool) or not math.isfinite(cap) or cap <= 0:
        raise ValueError("P10S1 config: resources.cap_hours must be a positive float")
    gen = data.get("generation")
    if not isinstance(gen, dict) or set(gen) != set(GENERATION_DEFAULT):
        raise ValueError("P10S1 config: [generation] needs cap_seconds, provisional and table_facts")
    if not isinstance(gen["cap_seconds"], float) or not math.isfinite(gen["cap_seconds"]) or gen["cap_seconds"] <= 0 or not isinstance(gen["provisional"], bool) or gen["table_facts"] not in (FACT_TABLE, OVERLOAD_FACTS):
        raise ValueError("P10S1 config: generation.cap_seconds a positive float, provisional a boolean, table_facts 32768 or 65536")
    _validate(data, registered_config(cap, gen), "P10S1 config")
    return data


def generation_settings(path: Path | None = None) -> dict[str, Any]:
    """The registered generation's cap per draw, whether it is still provisional (set by the rehearsal's measured G1 time: ``stages set-generation-cap``), and the fact table's size."""
    return dict(load_config(path)["generation"])


def load_config(path: Path | None = None) -> dict[str, Any]:
    with (path or repo_root() / DEFAULT_CONFIG).open("rb") as stream:
        return validate_config(tomllib.load(stream))


def cap_seconds(path: Path | None = None) -> float:
    """The charged-time cap in seconds, from ``resources.cap_hours`` of the config (never a constant of the code)."""
    return float(load_config(path)["resources"]["cap_hours"]) * 3600.0


def render_config_toml(cap_hours: float = CAP_HOURS_DEFAULT, generation: Mapping[str, Any] | None = None) -> str:
    """The canonical text of ``configs/p10s1_capacity.toml`` (a test requires byte equality up to the cap)."""
    from studies.p9i.core import _toml_lines

    header = [
        "# ADR-0021 revision 4 (P10S1) registered constants. Generated by studies.p10s1.core.render_config_toml",
        "# and validated against studies.p10s1.core; any difference is refused, except resources.cap_hours (the human lead's figure) and [generation] (set by the rehearsal and the freeze).",
        "",
    ]
    return "\n".join([*header, *_toml_lines(registered_config(cap_hours, generation), "")]) + "\n"


# --- identity hashes ----------------------------------------------------------------------------------------------------------------------------------
def source_hashes(root: Path | None = None) -> dict[str, str]:
    """SHA-256 of every ``studies/p10s1/*.py`` and launch script, of the imported ``studies/p9ii``, ``studies/p9i`` and ``studies/p9`` modules."""
    base = root or repo_root()
    out: dict[str, str] = {}
    for p in sorted((base / "studies" / "p10s1").glob("*.py")):
        out[f"studies/p10s1/{p.name}"] = file_sha256(p)
    for p in sorted((base / LAUNCH_DIR).glob("*.sh")):
        out[f"studies/p10s1/launch/{p.name}"] = file_sha256(p)
    for pkg, names in (("p9ii", IMPORTED_P9II_MODULES), ("p9i", IMPORTED_P9I_MODULES), ("p9", IMPORTED_P9_MODULES)):
        for name in names:
            out[f"studies/{pkg}/{name}.py"] = file_sha256(base / "studies" / pkg / f"{name}.py")
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
    """Operating system, machine, processor, Python and torch versions and thread settings (every run manifest carries it, section 7.6)."""

    def version(package: str) -> str | None:
        try:
            return metadata.version(package)
        except metadata.PackageNotFoundError:
            return None

    return {
        "platform": platform.platform(), "system": platform.system(), "release": platform.release(), "machine": platform.machine(), "processor": platform.processor(),
        "python": sys.version, "python_implementation": platform.python_implementation(), "torch": torch.__version__, "psutil": version("psutil"), "cpu_count": os.cpu_count(),
        "threads": {
            "torch_num_threads": torch.get_num_threads(), "torch_interop_threads": torch.get_num_interop_threads(),
            "deterministic_algorithms": bool(torch.are_deterministic_algorithms_enabled()),
            "env": {k: os.environ.get(k) for k in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "PYTHONHASHSEED")},
        },
        "delegated_models": "recorded from session metadata by the lead, not by this code",
    }  # fmt: skip


# --- run names, records and paths --------------------------------------------------------------------------------------------------------------------------
STAGE_CODES: dict[str, str] = {
    "generate": "P", "drawplan": "L", "calibrate": "C", "rehearse": "H", "gates": "G", "train": "T", "evaluate": "E", "timing": "M", "simulate": "S",
    "analyze": "A", "report": "R", "dry": "D", "freeze": "F", "synthetic": "Y",
}  # fmt: skip
RECORD_KINDS = (
    "train", "snapshot", "eval", "baseline", "stage_manifest", "calibration", "rehearsal", "analysis", "data_manifest", "gates", "draw_plan", "projection", "ledger",
    "timing", "throughput", "simulation", "freeze_plan", "stage_caps", "mc_plan",
)  # fmt: skip
PANELS = ("A", "B")
PANEL_STREAM = {"A": "panel_a", "B": "panel_b"}
SECONDARY_STREAMS = {"H1": "h1", "H2": "h2"}


def utc_stamp(now: datetime | None = None) -> str:
    return (now or datetime.now(UTC)).strftime("%Y%m%dT%H%M%S%fZ")


def run_name(stage: str, now: datetime | None = None, unique: str | None = None) -> str:
    """``P10S1<code>-<utc>-<uuid hex>`` for a stage in ``STAGE_CODES``."""
    if stage not in STAGE_CODES:
        raise ValueError(f"unknown P10S1 stage {stage!r}")
    return f"{STUDY}{STAGE_CODES[stage]}-{utc_stamp(now)}-{unique or uuid.uuid4().hex}"


def parse_run_name(name: str) -> tuple[str, str, str]:
    head, _, rest = name.partition("-")
    stamp, _, unique = rest.partition("-")
    codes = {code: stage for stage, code in STAGE_CODES.items()}
    if not head.startswith(STUDY) or head[len(STUDY) :] not in codes or not stamp.endswith("Z") or not unique:
        raise ValueError(f"not a P10S1 run name: {name!r}")
    return codes[head[len(STUDY) :]], stamp, unique


def envelope(kind: str) -> dict[str, Any]:
    if kind not in RECORD_KINDS:
        raise ValueError(f"unknown record kind {kind!r}")
    return {"kind": kind, "schema": SCHEMA, "study": STUDY}


def write_record(path: Path, record: Mapping[str, Any]) -> None:
    """Atomically write a JSON record (canonical, no NaN) after checking its envelope keys."""
    if record.get("study") != STUDY or record.get("schema") != SCHEMA or record.get("kind") not in RECORD_KINDS:
        raise ValueError("P10S1 record needs study, schema and a registered kind")
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, dict(record))


def read_record(path: Path, kind: str | None = None) -> dict[str, Any]:
    record = read_json(path)
    if not isinstance(record, dict) or record.get("study") != STUDY or record.get("schema") != SCHEMA:
        raise ValueError(f"not a P10S1 record: {path}")
    if kind is not None and record.get("kind") != kind:
        raise ValueError(f"expected a {kind!r} record, got {record.get('kind')!r}: {path}")
    return record


def cell_dir(run_dir: Path, label: str) -> Path:
    parse_label(label)
    return run_dir / "cells" / label


def eval_path(run_dir: Path, label: str, update: int) -> Path:
    return cell_dir(run_dir, label) / "eval" / snapshot_stem(update) / "eval.json"


def default_experiments_root() -> Path:
    return p9core.default_experiments_root()


# --- the charged-time ledger (section 10.3) -------------------------------------------------------------------------------------------------------------------
class LedgerRefused(RuntimeError):
    """A stage cannot start: the remainder of the cap is smaller than the stage's own cap."""


class Ledger:
    """Charged wall time of the whole study (calibration, rehearsal and every registered stage). Entries are appended to one JSON file; nothing is removed. The cap
    is the value of ``resources.cap_hours`` of the config (the human lead's figure; this class never holds a number of its own). A stage refuses to start when the
    remainder of the cap is smaller than its own stage cap and is charged what it used."""

    def __init__(self, path: Path, cap_seconds: float) -> None:
        if not math.isfinite(cap_seconds) or cap_seconds <= 0:
            raise ValueError("the cap must be a positive number of seconds")
        self.path, self.cap_seconds = path, float(cap_seconds)

    @classmethod
    def from_config(cls, root: Path, config_path: Path | None = None) -> "Ledger":
        return cls(root / f"{STUDY}-ledger.json", cap_seconds(config_path))

    def entries(self) -> list[dict[str, Any]]:
        if not self.path.is_file():
            return []
        data = read_json(self.path)
        if not isinstance(data, dict) or data.get("study") != STUDY or data.get("kind") != "ledger":
            raise ValueError(f"not a P10S1 ledger: {self.path}")
        return list(data["entries"])

    def charged(self) -> float:
        return float(sum(float(e["seconds"]) for e in self.entries()))

    def remaining(self) -> float:
        return max(0.0, self.cap_seconds - self.charged())

    def require_room(self, stage: str, stage_cap_seconds: float) -> None:
        if not math.isfinite(stage_cap_seconds) or stage_cap_seconds <= 0:
            raise LedgerRefused(f"stage {stage}: the stage cap must be a positive number")
        if self.remaining() < stage_cap_seconds:
            raise LedgerRefused(
                f"stage {stage}: {self.remaining():.0f} s of the {self.cap_seconds:.0f} s cap remain, less than the stage cap of {stage_cap_seconds:.0f} s; the study is S1-INCOMPLETE "
                "and the work returns to the human lead"
            )

    def charge(self, stage: str, run: str, seconds: float) -> None:
        entries = self.entries()
        entries.append({"stage": stage, "run": run, "seconds": max(0.0, float(seconds)), "utc": datetime.now(UTC).isoformat()})
        self.path.parent.mkdir(parents=True, exist_ok=True)
        write_json(self.path, {"study": STUDY, "kind": "ledger", "cap_seconds": self.cap_seconds, "entries": entries})


# --- non-finite numbers in records (P9-I's reading) ----------------------------------------------------------------------------------------------------------------
NONFINITE = p9icore.NONFINITE
nonfinite_str = p9icore.nonfinite_str
jsonable = p9icore.jsonable
number = p9icore.number


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def derive_seed(seed: int, *tags: object) -> int:
    """A 62-bit seed derived from ``seed`` and tags (SHA-256)."""
    text = "|".join([str(seed), "p10s1", *map(str, tags)]).encode()
    return int.from_bytes(hashlib.sha256(text).digest()[:8], "little") & ((1 << 62) - 1)


def json_line(record: Mapping[str, Any]) -> str:
    return json.dumps(jsonable(dict(record)), allow_nan=False, sort_keys=True)
