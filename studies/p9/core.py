# ruff: noqa: E501
"""P9 shared contract: constants, the 100-cell registry, schedules, coefficients, record schemas,
identity helpers and record IO.

Specification: docs/decisions/ADR-0017-parallel-capacity-and-locality-diagnostics.md (revision 3,
human decision 1 given: implementation, calibration and rehearsal only; the registered run is NOT
authorized). Every constant below is copied from that ADR; where the ADR leaves an implementation
detail open, the choice is listed in ``OPEN_CHOICES`` (also written to the config) and is PENDING
LEAD REVIEW. Nothing here trains or evaluates a model.

Position convention, fixed for all modules (INTERFACE_CONTRACT.md): a context is 64 bytes; the model
input is bytes 0..62 and the targets are bytes 1..63; record ``r`` occupies bytes ``8r..8r+7``
(separator, five identifier bytes, binding byte, answer byte); the answer site of record ``r`` is
input position ``8r+6`` and its target is byte ``8r+7``.

Status: implementation self-checked only. Not independent review, not Astra validation, not human
approval.
"""

import hashlib
import json
import math
import subprocess
import tomllib
import uuid
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, NamedTuple, TypedDict

from arborlm.config import _validate
from arborlm.io import canonical_json, file_sha256, read_json, sha256, write_json

if TYPE_CHECKING:
    from torch import Tensor

# --- identity of the study ---------------------------------------------------------------------
SPEC = "docs/decisions/ADR-0017-parallel-capacity-and-locality-diagnostics.md"
STUDY = "P9"
FAMILY = "P9_PARALLEL_CAPACITY_LOCALITY_DIAGNOSTICS"
SCHEMA = 1
DEFAULT_CONFIG = Path("configs/p9_diagnostics.toml")
FROZEN_SOURCE_DIGEST = "8b5a03a08fc10a4ac29bdf9c6dd2d21945b9bb3aff459766b58304545d570507"
P5_SUITE = "P5HIER-20261113T125206040109Z-8a40c493791641028f8eb8dfa26f71be"
P5_QUALITY = "P5QUALITY-20261113T125206040450Z-aa1f203f012e4112bf137cd09944bb92"
P1_TRAIN_SHA256 = "1c3e7a3e02087392ae3db874935517c66e77f15d7a50c3285a8c5ba5d7fabd07"
CORPUS_ROW_BYTES, CORPUS_TRAIN_ROWS, CORPUS_TRAINED_ROWS = 65, 4096, 2048

# --- the planted-fact task (ADR section 4) ----------------------------------------------------------
ALPHABET: tuple[int, ...] = tuple(
    range(0x40, 0x60)
)  # open choice 1: '@', 'A'..'Z', '[', '\\', ']', '^', '_'
ALPHABET_SIZE = 32
IDENTIFIER_LENGTH, FREE_SYMBOLS, CHECKSUM_MODULUS, ANSWER_LENGTH = 5, 4, 32, 1
CLUSTER_SIZE = 16
UNSEEN_FACTS = 2048
RECORD_BYTES, RECORDS_PER_CONTEXT, CONTEXT_BYTES = 8, 8, 64
INPUT_LENGTH, TARGETS_PER_CONTEXT, ANSWER_SITES_PER_CONTEXT = 63, 63, 8
ANSWER_INPUT_OFFSET, ANSWER_TARGET_OFFSET = 6, 7  # within a record
KNOCKOUT_POSITIONS = 7  # input positions 8r .. 8r+6 of a record (section 6.2)
BATCH_CONTEXTS = 16
ANSWER_SITES_PER_BATCH = BATCH_CONTEXTS * ANSWER_SITES_PER_CONTEXT  # 128
BITS_PER_FACT = 5.0

SLOTS_BY_SIZE: tuple[int, ...] = (4096, 16384, 65536)
FACTS_PROPORTIONAL: dict[int, int] = {4096: 2048, 16384: 8192, 65536: 32768}
FACTS_FIXED_TRACK = 2048
BRANCHES: dict[int, int] = {4096: 16, 16384: 64, 65536: 256}
PER_BRANCH, VISIT = 256, 2
TOP, TEMPERATURE = 8, 0.2
KEY_WIDTH, KEY_WIDTH_WIDE, VALUE_WIDTH, HIDDEN_WIDTH = 16, 32, 32, 32
KEY_WIDTHS = (KEY_WIDTH, KEY_WIDTH_WIDE)
GATE_INIT, INIT_STD = -2.0, 0.02
SOFT_TOP = 64  # candidates on which the soft inclusion is computed
LANE_D_FACTS = 4096  # per phase (sets A and B)
LANE_D_JOINT_FACTS = 2 * LANE_D_FACTS
LANE_D_SLOTS = 16384

# --- optimization and exposure (section 5) --------------------------------------------------------
LEARNING_RATE, WEIGHT_DECAY, BETAS, ADAM_EPS, CLIP_NORM = 0.003, 0.0, (0.9, 0.999), 1e-8, 1.0
LAZY_LEARNING_RATE = 0.012  # section 5.6, lead's choice; key and value tables only
LAZY_TABLES = ("keys", "values")
EXPOSURE_MENU = (32, 64, 128)
DEFAULT_EXPOSURE = 32
UPDATE_ANSWER_EXPOSURES = ANSWER_SITES_PER_BATCH  # U_N = F * E / 128
FIXED_COMPUTE_FACTS = FACTS_PROPORTIONAL[16384]  # U_16K = 8192 * E / 128 at every size

# --- objectives (section 7) -----------------------------------------------------------------------
BETA_SOFT = 0.25  # pi_s = sigmoid((score_s - tau) / 0.25)
CO_GROUP = 8  # 8-slot identifier groups of R_co (ADR-0015)
CO_BEST = 1.0 / 8.0
ALPHA_U_DOSES = (0.0, 0.25, 1.0)
ALPHA_C_DOSES = (0.0, 0.05, 0.25)
ALPHA_C_WITH_ALPHA_U = 0.25  # the non-zero alpha_c only together with this alpha_u
CHANCE_LOSS_NATS = math.log(ALPHABET_SIZE)

# --- measurements and thresholds (sections 6 and 8): data only, applied by the analysis modules ------
CHANCE = 1.0 / ALPHABET_SIZE
G2_ALPHA = 0.001
G2_TESTS_PRIMARY, G2_TESTS_LANE_D = 8, 4
G1_TESTS_PER_STREAM, G1_PERMUTATIONS_PER_TEST, G1_P_THRESHOLD = 8, 2000, 0.001
G3_R2_ACCURACY = 0.95
SUPPORT_P_ABSOLUTE, SUPPORT_P_MARGIN = 2.0 / 32.0, 0.02
SPECIFICITY_OTHER_SLOTS, SPECIFICITY_DELTA, SPECIFICITY_SHARE = 8, 0.05, 0.95
SPECIFICITY_GROUPS, SPECIFICITY_GROUP_TOLERANCE = 64, 0.02
STEP_ACCURACY_MIN, STEP_RATIO_B101, STEP_RATIO_B102 = 0.25, 3.0, 2.5
NOT_SUPPORTED_RATIO, BEATS_DENSE_RATIO = 2.0, 1.10
DEPENDENCE_SUPPORT_SHARE, PLATEAU_FRACTION, POSITIVE_ACCURACY_64K = 0.90, 0.05, 0.50
EMPTY_SLOT_RISE = 0.25
TREE_AHEAD_RATIO, TREE_COMPETITIVE_RATIO = 1.03, 0.97
LADDER_MATERIAL_BITS = 0.5
LANE_B_MIN_ACCURACY = 0.25
UTIL_USTAR_COLLAPSED, UTIL_I_COLLAPSED = 0.80, 0.90
UTIL_EFF_INFLATION, UTIL_NO_GAIN = 1.25, 1.03
UTIL_IMPROVED, UTIL_SUPPORT_LENGTH_MAX = 1.05, 1.10
UTIL_PRESERVED, UTIL_ACCURACY_DROP_MAX = 0.97, 0.02
SOFT_USAGE_ONLY_RATIO = 1.05
REGULARIZER_MOVEMENT_RATIO = 1.5
CACHE_RHOS_PRIMARY, CACHE_ROWS_PRIMARY = (1.0 / 16.0, 1.0 / 4.0), (8, 32)
CACHE_RHOS_SWEEP, CACHE_ROWS_SWEEP = (1.0 / 16.0, 1.0 / 4.0, 1.0), (2, 8, 32)
NULL_REPLICATES, E_NULL_FLOOR = 3, 0.05
LOCALITY_E_RATIO_POSITIVE, LOCALITY_E_RATIO_BAND = 0.80, (0.90, 1.10)
LOCALITY_QUALITY_RATIO = 0.97
TIE_RULES = ("asc", "desc")
LANE_D_A0_MIN, LANE_D_NO_NEW, LANE_D_FORGETTING = 0.5, 0.5, 0.70
LANE_D_POSITIVE_B, LANE_D_POSITIVE_A = 0.9, 0.90
LANE_D_FORGETTING_GAP, LANE_D_DENSE_FORGETTING_MAX = 0.10, 0.10

# --- seeds (section 10) -----------------------------------------------------------------------------
DATA_SEEDS: dict[str, int] = {
    "facts": 170001,
    "templates": 170011,
    "clusters": 170031,
    "training_order": 170041,
    "calibration_stream": 170051,
    "panel_a": 170061,
    "panel_b": 170071,
    "held_out": 170081,
    "mixed_cluster": 170082,
    "lane_d_a": 170091,
    "lane_d_b": 170092,
    "r1_codes": 170101,
    "branch_hash": 170102,
    "permutation_tests": 170111,
}
NULL_SEEDS_A = (171331, 171332, 171333)
NULL_SEEDS_B = (171341, 171342, 171343)
INIT_SEEDS = (1701, 1702)
PRIMARY_PARENT, REPLICATE_PARENT = (101, 301), (102, 302)
REHEARSAL_SEED_BASE = (
    179001  # rehearsal and calibration seeds: 179001 upward, in no registered cell
)

# --- resources (section 11, decision 1) -------------------------------------------------------------
RSS_WORKER_BYTES = 3 * 1024**3
RSS_AGGREGATE_BYTES = 24 * 1024**3
TRAINING_WORKERS_RANGE, SIMULATION_WORKERS = (2, 4), 4
CALIBRATION_REHEARSAL_HOURS = 4.0  # the lead's application of decision 1; the run cap is not fixed

# --- cells and blocks (section 10) ------------------------------------------------------------------
ARCHS = ("flat", "fixed_tree", "learned_tree", "dense")
RUNGS = ("R0", "R0a", "R1", "R2", "OB")
TRACKS = ("proportional", "fixed")
OPTIMIZERS = ("adamw", "lazy")
PROPORTIONAL, FIXED_TRACK, ADAMW, LAZY = "proportional", "fixed", "adamw", "lazy"
LANE_D_ARMS = ("phaseA", "sequential", "memory_only", "replay", "joint")
BLOCKS = ("A1", "A2", "A3", "A4", "A5", "A5b", "A6", "A7", "A8", "A10", "B1", "C1", "D1", "D2")
BLOCK_COUNTS: dict[str, int] = {
    "A1": 9,
    "A2": 9,
    "A3": 2,
    "A4": 4,
    "A5": 12,
    "A5b": 4,
    "A6": 4,
    "A7": 8,
    "A8": 6,
    "A10": 6,
    "B1": 8,
    "C1": 8,
    "D1": 6,
    "D2": 14,
}
BLOCK_LANE: dict[str, str] = {
    **dict.fromkeys(("A1", "A2", "A3", "A4", "A5", "A5b", "A6", "A7", "A8", "A10"), "A"),
    "B1": "B",
    "C1": "C",
    "D1": "D",
    "D2": "D",
}
TOTAL_CELLS = 100
_ARCH_CODE = {"flat": "flat", "fixed_tree": "fixtree", "learned_tree": "tree", "dense": "dense"}

# analysis-level dependencies (section 10, "Analysis:"): item -> blocks it needs
ANALYSIS_DEPENDENCIES: dict[str, tuple[str, ...]] = {
    "capacity_flat": ("A1", "A8"),  # A1 at all sizes including the B102 replicate
    "capacity_tree": ("A2", "A8"),  # A2 at all sizes including the B102 replicate
    "annotation_empty_slot": ("A4", "A1"),  # A1 at 4K only
    "annotation_optimizer": ("A10", "A1"),
    "annotation_key_width": ("A7", "A1"),
    "annotation_tree_ahead": ("A1", "A2", "A3"),  # at 16K
    "utilization_b1": ("B1", "A1", "A2"),  # A1/A2 at 16K
    "locality_c1": ("C1", "A1", "B1"),  # A1 16K flat; B1 alpha_u = 0.25
    "lane_c_gate": ("A1", "A2", "B1"),  # A1/A2 at 4K and 16K; B1 alpha_u = 0.25 cells
    # added by I0 from CONFIRM.md's optional note (not stated in the ADR's paragraph):
    "ladder": ("A5", "A5b", "A6", "A7", "A1", "A2"),
    "lane_d": ("D1", "D2"),
}


@dataclass(frozen=True)
class Cell:
    """One of the 100 registered training cells (ADR section 10).

    ``depends_on`` lists the labels of cells that must have completed first (training dependencies
    only: each D2 sequential, memory-only or replay arm needs the D1 cell of the same architecture,
    parent and seed). Analysis dependencies are in ``ANALYSIS_DEPENDENCIES``.
    """

    block: str
    arch: str
    slots: int
    key_width: int
    rung: str
    track: str
    facts: int
    optimizer: str
    alpha_u: float
    alpha_c: float
    parent: tuple[int, int]
    seed: int
    lane_d_arm: str | None
    index: int
    label: str
    depends_on: tuple[str, ...]

    def __post_init__(self) -> None:
        if (
            self.block not in BLOCKS
            or self.arch not in ARCHS
            or self.rung not in RUNGS
            or self.track not in TRACKS
            or self.optimizer not in OPTIMIZERS
            or self.slots not in SLOTS_BY_SIZE
            or self.key_width not in KEY_WIDTHS
            or self.parent not in (PRIMARY_PARENT, REPLICATE_PARENT)
            or self.seed not in INIT_SEEDS
            or self.alpha_u not in ALPHA_U_DOSES
            or self.alpha_c not in ALPHA_C_DOSES
            or (self.lane_d_arm is not None and self.lane_d_arm not in LANE_D_ARMS)
            or self.facts <= 0
        ):
            raise ValueError(f"unregistered P9 cell: {self.label}")

    @property
    def backbone(self) -> int:
        return self.parent[0]

    @property
    def order(self) -> int:
        return self.parent[1]

    @property
    def parent_label(self) -> str:
        """The P5-P8 parent label used to find the frozen backbone (``b101-o301-baseline``)."""
        return f"b{self.backbone}-o{self.order}-baseline"

    @property
    def lane(self) -> str:
        return BLOCK_LANE[self.block]

    @property
    def is_lane_d(self) -> bool:
        return self.lane_d_arm is not None

    def fields(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class _Spec:
    block: str
    arch: str
    slots: int
    rung: str = "R0"
    key_width: int = KEY_WIDTH
    track: str = PROPORTIONAL
    optimizer: str = ADAMW
    alpha_u: float = 0.0
    alpha_c: float = 0.0
    lane_d_arm: str | None = None
    facts: int | None = None
    replicate: bool = False


def facts_for(slots: int, track: str = PROPORTIONAL) -> int:
    """Fact count of a size and track (ADR 4.1): proportional 2,048 / 8,192 / 32,768; fixed 2,048."""
    if track == FIXED_TRACK:
        return FACTS_FIXED_TRACK
    return FACTS_PROPORTIONAL[slots]


def _dose(value: float) -> str:
    return f"{value:g}".replace(".", "p")


def _label(spec: _Spec, parent: tuple[int, int], seed: int) -> str:
    parts = [spec.block, _ARCH_CODE[spec.arch], spec.rung, f"n{spec.slots}"]
    if spec.key_width != KEY_WIDTH:
        parts.append(f"k{spec.key_width}")
    if spec.track == FIXED_TRACK:
        parts.append("fixed")
    if spec.optimizer == LAZY:
        parts.append("lazy")
    if spec.alpha_u:
        parts.append(f"au{_dose(spec.alpha_u)}")
    if spec.alpha_c:
        parts.append(f"ac{_dose(spec.alpha_c)}")
    if spec.lane_d_arm:
        parts.append(spec.lane_d_arm)
    parts.append(f"b{parent[0]}-o{parent[1]}-s{seed}")
    return "-".join(parts)


def _specs() -> list[_Spec]:
    """The configurations of ADR section 10 in registry order (block order, then configuration)."""
    out: list[_Spec] = []
    for s in SLOTS_BY_SIZE:
        out.append(_Spec("A1", "flat", s, replicate=True))
    for s in SLOTS_BY_SIZE:
        out.append(_Spec("A2", "learned_tree", s, replicate=True))
    out.append(_Spec("A3", "fixed_tree", 16384))
    for s in (16384, 65536):
        out.append(_Spec("A4", "flat", s, track=FIXED_TRACK))
    for s in SLOTS_BY_SIZE:
        for rung in ("R1", "R2"):
            out.append(_Spec("A5", "flat", s, rung=rung))
    for s in (16384, 65536):
        out.append(_Spec("A5b", "flat", s, rung="R0a"))
    out.append(_Spec("A6", "learned_tree", 16384, rung="R1"))
    out.append(_Spec("A6", "learned_tree", 16384, rung="OB"))
    for s in (16384, 65536):
        for rung in ("R0", "R1"):
            out.append(_Spec("A7", "flat", s, rung=rung, key_width=KEY_WIDTH_WIDE))
    for s in SLOTS_BY_SIZE:
        out.append(_Spec("A8", "dense", s))
    for s in SLOTS_BY_SIZE:
        out.append(_Spec("A10", "flat", s, optimizer=LAZY))
    for arch in ("flat", "learned_tree"):
        for au in (0.25, 1.0):
            out.append(_Spec("B1", arch, 16384, alpha_u=au))
    for arch in ("flat", "learned_tree"):
        for ac in (0.05, 0.25):
            out.append(_Spec("C1", arch, 16384, alpha_u=ALPHA_C_WITH_ALPHA_U, alpha_c=ac))
    for arch in ("flat", "learned_tree", "dense"):
        out.append(_Spec("D1", arch, LANE_D_SLOTS, lane_d_arm="phaseA", facts=LANE_D_FACTS))
    for arch, arm, facts in (
        ("flat", "sequential", LANE_D_FACTS),
        ("flat", "memory_only", LANE_D_FACTS),
        ("learned_tree", "sequential", LANE_D_FACTS),
        ("flat", "replay", LANE_D_FACTS),
        ("dense", "sequential", LANE_D_FACTS),
        ("dense", "replay", LANE_D_FACTS),
        ("flat", "joint", LANE_D_JOINT_FACTS),
    ):
        out.append(_Spec("D2", arch, LANE_D_SLOTS, lane_d_arm=arm, facts=facts))
    return out


def _build_cells() -> list[Cell]:
    instances: list[tuple[_Spec, tuple[int, int], int]] = []
    for spec in _specs():
        for seed in INIT_SEEDS:
            instances.append((spec, PRIMARY_PARENT, seed))
        if spec.replicate:
            instances.append((spec, REPLICATE_PARENT, INIT_SEEDS[0]))
    labels = [_label(spec, parent, seed) for spec, parent, seed in instances]
    phase_a = {
        (spec.arch, parent, seed): label
        for (spec, parent, seed), label in zip(instances, labels, strict=True)
        if spec.block == "D1"
    }
    result: list[Cell] = []
    for index, ((spec, parent, seed), label) in enumerate(zip(instances, labels, strict=True)):
        depends: tuple[str, ...] = ()
        if spec.block == "D2" and spec.lane_d_arm != "joint":
            depends = (phase_a[(spec.arch, parent, seed)],)
        result.append(
            Cell(
                block=spec.block,
                arch=spec.arch,
                slots=spec.slots,
                key_width=spec.key_width,
                rung=spec.rung,
                track=spec.track,
                facts=spec.facts if spec.facts is not None else facts_for(spec.slots, spec.track),
                optimizer=spec.optimizer,
                alpha_u=spec.alpha_u,
                alpha_c=spec.alpha_c,
                parent=parent,
                seed=seed,
                lane_d_arm=spec.lane_d_arm,
                index=index,
                label=label,
                depends_on=depends,
            )
        )
    counts = {block: sum(1 for c in result if c.block == block) for block in BLOCKS}
    if counts != BLOCK_COUNTS or len(result) != TOTAL_CELLS:
        raise ValueError(f"P9 registry counts differ from ADR section 10: {counts}")
    if len({c.label for c in result}) != len(result):
        raise ValueError("P9 registry labels are not unique")
    if [c.index for c in result] != list(range(TOTAL_CELLS)):
        raise ValueError("P9 registry index order broken")
    known = {c.label for c in result}
    if any(d not in known for c in result for d in c.depends_on):
        raise ValueError("P9 registry dependency names an unknown cell")
    return result


_CELLS: list[Cell] = _build_cells()
_BY_LABEL: dict[str, Cell] = {c.label: c for c in _CELLS}


def cells() -> list[Cell]:
    """The 100 registered cells in index order (per-block counts asserted against ADR section 10)."""
    return list(_CELLS)


def parse_label(label: str) -> Cell:
    try:
        return _BY_LABEL[label]
    except KeyError:
        raise ValueError(f"unregistered P9 cell label: {label!r}") from None


def all_labels() -> list[str]:
    return [c.label for c in _CELLS]


def cells_of_block(block: str) -> list[Cell]:
    if block not in BLOCKS:
        raise ValueError(f"unknown P9 block: {block!r}")
    return [c for c in _CELLS if c.block == block]


# --- updates and snapshots (section 5.5) -------------------------------------------------------------
def _check_exposure(exposure: int) -> None:
    if exposure not in EXPOSURE_MENU:
        raise ValueError(f"exposure {exposure} is not in the menu {EXPOSURE_MENU}")


def matched_updates(facts: int, exposure: int) -> int:
    """U = F * E / 128 (a batch is 16 contexts = 128 answer-site exposures). Always an integer."""
    _check_exposure(exposure)
    product = facts * exposure
    if product % UPDATE_ANSWER_EXPOSURES:
        raise ValueError("F * E is not divisible by 128")
    return product // UPDATE_ANSWER_EXPOSURES


def fixed_compute_updates(exposure: int) -> int:
    """U_16K: the matched-exposure update count of the 16,384-slot proportional cell."""
    return matched_updates(FIXED_COMPUTE_FACTS, exposure)


def updates(cell: Cell, exposure: int) -> int:
    """The cell's own matched-exposure update count U_N = F * E / 128 (512 / 2,048 / 8,192 at E = 32
    for the proportional track; 1,024 for a Lane D phase of 4,096 facts)."""
    return matched_updates(cell.facts, exposure)


def run_updates(cell: Cell, exposure: int) -> int:
    """How many updates the cell is run for (open choices 6): Lane D cells run exactly ``updates``;
    every other cell runs ``max(U, U_16K)`` so that the fixed-compute snapshot exists (this makes the
    4,096-slot cells run to U_16K as the ADR states, and also the fixed-track cells)."""
    own = updates(cell, exposure)
    return own if cell.is_lane_d else max(own, fixed_compute_updates(exposure))


def snapshots(cell: Cell, exposure: int) -> tuple[int, ...]:
    """Sorted, distinct snapshot updates (with optimizer state). Non-Lane-D cells: U/2 and U of the
    cell's own matched-exposure point and U_16K/2 and U_16K. Lane D cells: U/2 and U (V1 is U of a D1
    cell). All values are exact integers; no rounding is ever needed."""
    own = updates(cell, exposure)
    marks = {own // 2, own}
    if not cell.is_lane_d:
        fixed = fixed_compute_updates(exposure)
        marks |= {fixed // 2, fixed}
    if any(m <= 0 for m in marks) or own % 2:
        raise ValueError("snapshot schedule requires an even, positive update count")
    return tuple(sorted(marks))


def contexts_per_update(cell: Cell) -> int:
    """16 contexts per batch; a replay arm adds one replayed A context per B context (open choice 7)."""
    return BATCH_CONTEXTS * (2 if cell.lane_d_arm == "replay" else 1)


def answer_exposures_per_update(cell: Cell) -> int:
    return contexts_per_update(cell) * ANSWER_SITES_PER_CONTEXT


# --- positions (the contract's convention) -----------------------------------------------------------
def answer_site_position(record: int) -> int:
    """Input position of record ``record``'s answer site (the binding byte): 8r + 6."""
    if not 0 <= record < RECORDS_PER_CONTEXT:
        raise ValueError("record index out of range")
    return RECORD_BYTES * record + ANSWER_INPUT_OFFSET


def answer_target_position(record: int) -> int:
    """Byte index of record ``record``'s answer byte (the target of its answer site): 8r + 7."""
    return answer_site_position(record) + 1


def record_input_positions(record: int) -> tuple[int, ...]:
    """The seven input positions 8r .. 8r+6 of a record (ADR 6.2 knock-out positions)."""
    base = RECORD_BYTES * record
    answer_site_position(record)
    return tuple(range(base, base + KNOCKOUT_POSITIONS))


ANSWER_SITE_POSITIONS: tuple[int, ...] = tuple(answer_site_position(r) for r in range(8))


# --- parameter counts and sizes (sections 5.2, 5.6) ----------------------------------------------------
def memory_parameters(arch: str, slots: int, key_width: int = KEY_WIDTH) -> int:
    """Trainable parameters of an R0/R0a memory: keys + values + query projection + output projection
    + gate, plus the router for the learned tree (the fixed tree's router is a buffer). The flat
    key-16 count at 4,096 slots is the P5 value 198,145; the learned tree adds 16 * 16 = 256."""
    base = (
        slots * key_width
        + slots * VALUE_WIDTH
        + key_width * HIDDEN_WIDTH
        + VALUE_WIDTH * HIDDEN_WIDTH
        + 1
    )
    if arch == "learned_tree":
        return base + BRANCHES[slots] * key_width
    if arch in ("flat", "fixed_tree"):
        return base
    raise ValueError(f"no memory parameter count for arch {arch!r}")


def dense_hidden_width(slots: int) -> int:
    """Hidden width h of the dense adapter (open choice 8): two bias-free linear maps 32 -> h -> 32
    and one gate (64 * h + 1 parameters, the P5 structure), matched to the flat key-16 memory of the
    same size, which it reproduces exactly (3,096 / 12,312 / 49,176)."""
    target = memory_parameters("flat", slots, KEY_WIDTH)
    width = (target - 1) // 64
    if abs(64 * width + 1 - target) / target > 0.001:
        raise ValueError("dense adapter cannot be matched within 0.1%")
    return width


def logical_key_products(arch: str, slots: int) -> int:
    """Logical key products per query (ADR 5.2; logical work, never measured efficiency)."""
    if arch == "flat":
        return slots
    if arch in ("fixed_tree", "learned_tree"):
        return BRANCHES[slots] + VISIT * PER_BRANCH
    raise ValueError(f"no logical key products for arch {arch!r}")


# --- coefficients (section 7) ---------------------------------------------------------------------------
def usage_floor_support(slots: int, facts: int) -> float:
    """M = min(N, 8F) / 2, the number of slots the global usage floor asks the memory to spread over."""
    return min(slots, 8 * facts) / 2.0


def usage_ema_rate(facts: int) -> float:
    """b = 128 / F: one pass over the facts."""
    return ANSWER_SITES_PER_BATCH / facts


def lambda_u(alpha_u: float, slots: int, facts: int) -> float:
    """lambda_u = alpha_u * ln 32 / (ln M / ln N): a fully collapsed memory costs alpha_u times the
    chance-level answer loss."""
    return (
        alpha_u * CHANCE_LOSS_NATS / (math.log(usage_floor_support(slots, facts)) / math.log(slots))
    )


def lambda_c(alpha_c: float) -> float:
    """lambda_c = alpha_c * ln 32 / (1 - 1/8), multiplying (R_co - 1/8)."""
    return alpha_c * CHANCE_LOSS_NATS / (1.0 - CO_BEST)


def lambda_u_for(cell: Cell) -> float:
    return lambda_u(cell.alpha_u, cell.slots, cell.facts)


def lambda_c_for(cell: Cell) -> float:
    return lambda_c(cell.alpha_c)


# --- chance interval, information (sections 6.1 and 8.1) -----------------------------------------------
def g2_level(tests: int = G2_TESTS_PRIMARY) -> float:
    """Level 1 - 0.001 / tests of the family of G2 tests (8 primary, 4 for Lane D)."""
    return 1.0 - G2_ALPHA / tests


class ChanceInterval(NamedTuple):
    n: int
    level: float
    low: int  # smallest count whose lower tail P(X <= low) exceeds the tail mass
    high: int  # largest count whose upper tail P(X >= high) exceeds the tail mass
    low_accuracy: float
    high_accuracy: float


def _binomial_pmf(n: int, p: float) -> list[float]:
    log_p, log_q = math.log(p), math.log1p(-p)
    top = math.lgamma(n + 1)
    return [
        math.exp(top - math.lgamma(k + 1) - math.lgamma(n - k + 1) + k * log_p + (n - k) * log_q)
        for k in range(n + 1)
    ]


def chance_interval(
    n: int, tests: int = G2_TESTS_PRIMARY, p: float = CHANCE, alpha: float = G2_ALPHA
) -> ChanceInterval:
    """Exact binomial central interval of level ``1 - alpha / tests`` around ``p`` for ``n`` facts
    (equal tail mass alpha / (2 * tests) on each side). ``[low, high]`` covers at least the level and
    each end is the tightest one that does."""
    if n <= 0 or tests <= 0:
        raise ValueError("n and tests must be positive")
    tail = alpha / tests / 2.0
    pmf = _binomial_pmf(n, p)
    cumulative, low = 0.0, 0
    for k, mass in enumerate(pmf):
        cumulative += mass
        if cumulative > tail:
            low = k
            break
    cumulative, high = 0.0, n
    for k in range(n, -1, -1):
        cumulative += pmf[k]
        if cumulative > tail:
            high = k
            break
    return ChanceInterval(n, 1.0 - alpha / tests, low, high, low / n, high / n)


def at_or_below_chance(correct: int, n: int, tests: int = G2_TESTS_PRIMARY) -> bool:
    """True when the accuracy is at or below the upper end of the G2 interval for ``n`` facts."""
    return correct <= chance_interval(n, tests).high


def fano_bits_per_fact(accuracy: float) -> float:
    """5 - h2(e) - e * log2(31) with e = 1 - accuracy (ADR 6.1; 0 at chance up to the Fano slack,
    0.046 at accuracy 0)."""
    e = 1.0 - accuracy
    h2 = 0.0 if e <= 0.0 or e >= 1.0 else -(e * math.log2(e) + (1.0 - e) * math.log2(1.0 - e))
    return BITS_PER_FACT - h2 - e * math.log2(ALPHABET_SIZE - 1)


def information_bits(correct: int, facts: int, tests: int = G2_TESTS_PRIMARY) -> float:
    """I_acc = F * [5 - h2(e) - e * log2 31] bits, set to 0 for a cell whose accuracy is at or below
    the upper end of the G2 interval for its fact count (ADR 6.1). ``correct`` counts facts whose
    most probable symbol within the alphabet is the answer, ties counted wrong."""
    if not 0 <= correct <= facts or facts <= 0:
        raise ValueError("correct must lie in [0, facts]")
    if at_or_below_chance(correct, facts, tests):
        return 0.0
    return facts * fano_bits_per_fact(correct / facts)


@dataclass
class AnswerScores:
    """Scores of answer-site predictions for ``Q`` facts, restricted to the 32-symbol alphabet.

    ``logp_sigma [Q, 32] float32`` log-probabilities renormalized over the alphabet; ``p_correct [Q]
    float32`` the renormalized probability of the correct symbol; ``correct [Q] bool`` argmax within
    the alphabet equals the answer, ties counted wrong; ``mass_sigma [Q] float32`` probability mass
    inside the alphabet under the full 256-way softmax; ``answer [Q] int64`` symbol indices 0..31.
    """

    logp_sigma: "Tensor"
    p_correct: "Tensor"
    correct: "Tensor"
    mass_sigma: "Tensor"
    answer: "Tensor"


def score_answer_sites(logits: "Tensor", answer: "Tensor") -> AnswerScores:
    """Score ``logits [Q, 256] float`` at answer sites against ``answer [Q] int64`` symbol indices
    (position in ``ALPHABET``). Implements the ADR 6.1 counting rule in one place."""
    import torch

    if logits.ndim != 2 or logits.shape[1] != 256 or answer.shape != logits.shape[:1]:
        raise ValueError("expected logits [Q,256] and answer [Q]")
    index = torch.tensor(ALPHABET, dtype=torch.int64, device=logits.device)
    z = logits.float()
    mass = z.softmax(-1)[:, index].sum(-1)
    inside = z[:, index]
    logp = inside.log_softmax(-1)
    rows = torch.arange(logits.shape[0], device=logits.device)
    chosen = inside[rows, answer]
    others = inside.clone()
    others[rows, answer] = -torch.inf
    return AnswerScores(
        logp_sigma=logp,
        p_correct=logp[rows, answer].exp(),
        correct=chosen > others.max(dim=-1).values,
        mass_sigma=mass,
        answer=answer.to(torch.int64),
    )


def select_exposure(r2_accuracy: Mapping[int, Mapping[int, float]]) -> tuple[int | None, list[int]]:
    """ADR 8.1 G3 and 12 step 4 (open choice 11): ``r2_accuracy[slots][E]`` is the R2 accuracy on the
    rehearsal panels. A size that does not reach 0.95 at E = 128 is TASK_CEILING_FAIL; E is the
    smallest of {32, 64, 128} at which R2 reaches 0.95 at every size that is not TASK_CEILING_FAIL.
    Returns ``(E or None if every size fails, sorted failed sizes)``."""
    top = EXPOSURE_MENU[-1]
    failed = sorted(s for s, curve in r2_accuracy.items() if curve.get(top, 0.0) < G3_R2_ACCURACY)
    live = [s for s in r2_accuracy if s not in failed]
    if not live:
        return None, failed
    for exposure in EXPOSURE_MENU:
        if all(r2_accuracy[s].get(exposure, 0.0) >= G3_R2_ACCURACY for s in live):
            return exposure, failed
    return None, failed  # unreachable: every live size reaches 0.95 at the top of the menu


# --- seeds ---------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class SeedSet:
    """Every data seed of a study draw. ``registered()`` is ADR section 10; ``rehearsal(k)`` is the
    disjoint namespace used by calibration, rehearsal and tests."""

    name: str
    facts: int
    templates: int
    clusters: int
    training_order: int
    calibration_stream: int
    panel_a: int
    panel_b: int
    held_out: int
    mixed_cluster: int
    lane_d_a: int
    lane_d_b: int
    r1_codes: int
    branch_hash: int
    permutation_tests: int
    null_seeds_a: tuple[int, ...]
    null_seeds_b: tuple[int, ...]

    def data_values(self) -> list[int]:
        return [getattr(self, name) for name in DATA_SEEDS]


def registered_seeds() -> SeedSet:
    return SeedSet(
        "registered",
        **DATA_SEEDS,
        null_seeds_a=NULL_SEEDS_A,
        null_seeds_b=NULL_SEEDS_B,
    )


REHEARSAL_STRIDE = 100  # rehearsal draw k uses seeds 179001 + 100 * k + (0 .. 24), then null seeds


def rehearsal_seeds(draw: int = 0) -> SeedSet:
    """Seeds of rehearsal / calibration draw ``draw`` (open choice 12): all at or above 179001 and
    disjoint from every registered seed and from other draws."""
    if draw < 0:
        raise ValueError("draw must be non-negative")
    base = REHEARSAL_SEED_BASE + REHEARSAL_STRIDE * draw
    values = {name: base + i for i, name in enumerate(DATA_SEEDS)}
    return SeedSet(
        f"rehearsal-{draw}",
        **values,
        null_seeds_a=tuple(base + 20 + i for i in range(3)),
        null_seeds_b=tuple(base + 30 + i for i in range(3)),
    )


def registered_seed_values() -> frozenset[int]:
    seeds = registered_seeds()
    return frozenset(
        [*seeds.data_values(), *NULL_SEEDS_A, *NULL_SEEDS_B, *INIT_SEEDS, *DATA_SEEDS.values()]
    )


def assert_not_registered_seed(seed: int) -> None:
    """Rehearsal, calibration and test code calls this on every seed it uses."""
    if seed < REHEARSAL_SEED_BASE or seed in registered_seed_values():
        raise ValueError(
            f"seed {seed} is not in the rehearsal namespace (>= {REHEARSAL_SEED_BASE})"
        )


# --- open implementation choices (all PENDING LEAD REVIEW) -----------------------------------------------
TEMPLATE_POOL: tuple[int, ...] = (
    32, 101, 116, 97, 105, 110, 111, 114, 115, 104, 108, 100, 99, 117, 109, 102,
    103, 112, 119, 121, 98, 44, 118, 46, 107, 49, 48, 34, 50, 57, 39, 45,
    120, 41, 40, 53, 51, 52, 56, 122, 55, 54, 106, 113, 59, 128, 226, 195,
)  # fmt: skip
TEMPLATE_POOL_SIZE = 48
OPEN_CHOICES: dict[str, str] = {
    "c01_alphabet": "32 contiguous printable ASCII bytes 0x40..0x5F ('@', A-Z, '[', backslash, ']', '^', '_')",
    "c02_template_pool": (
        "count every byte in the first 2048 rows (ranks 0..2047, the rows the backbones were trained "
        "on) of the frozen P5 train.bytes (SHA-256 verified against P1_TRAIN_SHA256, 65 bytes per "
        "row); drop the 32 alphabet bytes; sort by (count descending, byte ascending); take 48"
    ),
    "c03_template_split": (
        "random.Random(templates_seed).shuffle of the 48-byte pool in rank order; positions 0-31 -> "
        "T (0-15 separators, 16-31 binding bytes, paired by index), 32-39 -> H1, 40-47 -> H2 (first "
        "four separators, last four binding bytes); 8 of the 16 (separator, binding) combinations "
        "per held-out set by random.Random(templates_seed + 1)"
    ),
    "c04_fact_nesting": (
        "one seeded fact table: proportional facts are the first F facts, so the fixed track and the "
        "4,096-slot cells use the same 2,048 facts as a prefix; cluster of fact i is i // 16 after "
        "the seeded fact order; unseen controls follow the trained facts; Lane D sets A (ids 0..4095) "
        "and B (4096..8191) form a second table whose identifiers avoid the main table's"
    ),
    "c05_snapshot_rounding": "none needed: U = F*E/128 is an even integer for every registered F and E",
    "c06_run_length": (
        "non-Lane-D cells run max(U, U_16K) updates, so the fixed-track cells also run to U_16K; Lane D "
        "cells run exactly U (E exposures per phase) with snapshots U/2 and U"
    ),
    "c07_replay": "a replay arm uses 16 B contexts plus 16 replayed A contexts per update; update count = U",
    "c08_dense_adapter": "bias-free 32 -> h -> 32, one gate, h = (P_flat_key16 - 1) // 64, flat key-16 count at the same N",
    "c09_g1_tests": (
        "k = 8 independence tests per stream (identifier positions 1-5, template, cluster, record "
        "index); permutations = 2000 * k"
    ),
    "c10_exact_unseen": "exact retrieval answers unseen facts with symbol index 0",
    "c11_exposure_rule": "sizes failing 0.95 at E = 128 are TASK_CEILING_FAIL and excluded when choosing E",
    "c12_rehearsal_seeds": "draw k uses 179001 + 100k + i for the 14 data seeds, null seeds at +20 and +30",
    "c13_run_names": "P9<code>-<utc %Y%m%dT%H%M%S%fZ>-<uuid4 hex>, code per stage in RUN_STAGE_CODES",
    "c14_dependencies": "Cell.depends_on holds training dependencies only; analysis dependencies are block-level",
    "c15_interval_tails": "central interval: tail mass 0.001 / (2 * tests) on each side, counts, not accuracies",
}

# --- run directories, identities and the frozen-input check ----------------------------------------------
RUN_STAGE_CODES: dict[str, str] = {
    "calibrate": "C",
    "rehearse": "H",
    "panel": "P",
    "train": "T",
    "evaluate": "E",
    "simulate": "S",
    "incremental": "D",
    "store": "V",
    "analyze": "A",
}
RECORD_KINDS = (
    "train",
    "snapshot",
    "eval",
    "trace",
    "sim",
    "stage_manifest",
    "calibration",
    "rehearsal",
)
REHEARSAL_RECORD_KEYS = frozenset(
    {
        "kind",
        "schema",
        "study",
        "label",
        "mode",
        "stage",
        "identity",
        "updates",
        "wall_seconds",
        "seconds_per_update",
        "peak_rss_bytes",
        "sampled_rss_bytes",
        "load_average",
        "loss_finite",
        "parameters_finite",
        "gradients_finite",
        "shapes",
        "parameter_counts",
        "trainable_parameters",
        "stored_parameters",
        "optimizer_state_bytes",
    }
)  # the whitelist of ADR 12 step 5: time, RSS, finiteness, shapes (no loss or accuracy value)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def utc_stamp(now: datetime | None = None) -> str:
    return (now or datetime.now(UTC)).strftime("%Y%m%dT%H%M%S%fZ")


def run_name(stage: str, now: datetime | None = None, unique: str | None = None) -> str:
    """``P9<code>-<utc>-<uuid hex>`` for a stage in ``RUN_STAGE_CODES``."""
    if stage not in RUN_STAGE_CODES:
        raise ValueError(f"unknown P9 stage {stage!r}")
    return f"P9{RUN_STAGE_CODES[stage]}-{utc_stamp(now)}-{unique or uuid.uuid4().hex}"


def parse_run_name(name: str) -> tuple[str, str, str]:
    """Inverse of ``run_name``: returns ``(stage, utc stamp, unique id)``."""
    head, _, rest = name.partition("-")
    stamp, _, unique = rest.partition("-")
    codes = {code: stage for stage, code in RUN_STAGE_CODES.items()}
    if not head.startswith("P9") or head[2:] not in codes or not stamp.endswith("Z") or not unique:
        raise ValueError(f"not a P9 run name: {name!r}")
    return codes[head[2:]], stamp, unique


def p9_source_hashes(root: Path | None = None) -> dict[str, str]:
    """SHA-256 of every ``*.py`` file under ``studies/p9/`` (relative names, sorted)."""
    base = (root or repo_root()) / "studies" / "p9"
    return {
        f"studies/p9/{p.relative_to(base).as_posix()}": file_sha256(p)
        for p in sorted(base.rglob("*.py"))
    }


def p9_source_digest(root: Path | None = None) -> str:
    """The P9 source digest: same recipe as the frozen P8 source digest, over ``studies/p9/**/*.py``."""
    return sha256(canonical_json(p9_source_hashes(root)))


def spec_sha256(root: Path | None = None) -> str:
    return file_sha256((root or repo_root()) / SPEC)


def config_sha256(path: Path | None = None) -> str:
    return sha256(canonical_json(load_config(path)))


class Identity(TypedDict):
    """Compact identity written into every record."""

    source_sha256: str  # P9 source digest
    spec_sha256: str
    config_sha256: str
    frozen_source_sha256: str  # arborlm.p8_core.source_digest(), must equal FROZEN_SOURCE_DIGEST


def code_identity(root: Path | None = None) -> Identity:
    from arborlm import p8_core

    return Identity(
        source_sha256=p9_source_digest(root),
        spec_sha256=spec_sha256(root),
        config_sha256=config_sha256((root or repo_root()) / DEFAULT_CONFIG),
        frozen_source_sha256=p8_core.source_digest(),
    )


def _git(repo: Path, *args: str) -> bytes:
    done = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=False)
    if done.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {done.stderr.decode().strip()}")
    return done.stdout


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data, usedforsecurity=False).hexdigest()


def frozen_input_check(
    repo: Path | None = None, commit: str = "HEAD", *, check_p8_digest: bool = True
) -> dict[str, Any]:
    """Verify that every ``src/arborlm/**/*.py`` file, ``uv.lock`` and ``pyproject.toml`` of the
    working tree equals its git blob at ``commit`` (no file missing, added or changed), and that
    ``arborlm.p8_core.source_digest()`` is still ``FROZEN_SOURCE_DIGEST``. Never repairs anything."""
    root = repo or repo_root()
    resolved = _git(root, "rev-parse", "--verify", f"{commit}^{{commit}}").decode().strip()
    listing = _git(
        root,
        "ls-tree",
        "-r",
        "--full-tree",
        resolved,
        "--",
        "src/arborlm",
        "uv.lock",
        "pyproject.toml",
    )
    blobs: dict[str, str] = {}
    for line in listing.decode().splitlines():
        meta, _, path = line.partition("\t")
        blobs[path] = meta.split()[2]
    tracked = {p for p in blobs if p.startswith("src/arborlm/") and p.endswith(".py")}
    tracked |= {"uv.lock", "pyproject.toml"}
    present = {p.relative_to(root).as_posix() for p in (root / "src" / "arborlm").rglob("*.py")}
    present |= {name for name in ("uv.lock", "pyproject.toml") if (root / name).is_file()}
    problems: list[str] = []
    for path in sorted(tracked | present):
        if path not in present:
            problems.append(f"{path}: in the commit, missing from the working tree")
        elif path not in blobs:
            problems.append(f"{path}: in the working tree, not in the commit")
        elif git_blob_sha1((root / path).read_bytes()) != blobs[path]:
            problems.append(f"{path}: differs from its blob at {resolved[:12]}")
    digest: str | None = None
    if check_p8_digest:
        from arborlm import p8_core

        digest = p8_core.source_digest(root / "src" / "arborlm")
        if digest != FROZEN_SOURCE_DIGEST:
            problems.append(f"frozen source digest changed: {digest}")
    return {
        "ok": not problems,
        "problems": problems,
        "commit": resolved,
        "files_compared": len(tracked),
        "source_digest": digest,
    }


def main_checkout(repo: Path | None = None) -> Path:
    """The main checkout (where the git-ignored ``experiments/`` and ``data/`` live)."""
    common = _git(repo or repo_root(), "rev-parse", "--path-format=absolute", "--git-common-dir")
    return Path(common.decode().strip()).parent


def default_experiments_root(repo: Path | None = None) -> Path:
    return main_checkout(repo) / "experiments"


# --- template pool from the backbone's training bytes ------------------------------------------------------
def corpus_path(experiments_root: Path) -> Path:
    return experiments_root / P5_SUITE / "quality" / P5_QUALITY / "frozen-data" / "train.bytes"


def load_trained_corpus(experiments_root: Path) -> bytes:
    """The first 2,048 rows (133,120 bytes) of the frozen train.bytes, verified by SHA-256. Reads
    nothing else: no validation or evaluation file."""
    raw = corpus_path(experiments_root).read_bytes()
    if sha256(raw) != P1_TRAIN_SHA256 or len(raw) != CORPUS_TRAIN_ROWS * CORPUS_ROW_BYTES:
        raise ValueError("P9 frozen training bytes mismatch")
    return raw[: CORPUS_TRAINED_ROWS * CORPUS_ROW_BYTES]


def derive_template_pool(corpus: bytes) -> tuple[int, ...]:
    """The 48 most frequent corpus bytes that are not in the alphabet, ordered by (count descending,
    byte ascending) (open choice 2). Deterministic; a function of the bytes only."""
    counts = [0] * 256
    for byte in corpus:
        counts[byte] += 1
    allowed = sorted(
        (b for b in range(256) if b not in ALPHABET and counts[b] > 0),
        key=lambda b: (-counts[b], b),
    )
    if len(allowed) < TEMPLATE_POOL_SIZE:
        raise ValueError("corpus has fewer than 48 distinct non-alphabet bytes")
    return tuple(allowed[:TEMPLATE_POOL_SIZE])


# --- config (a literal mirror of the constants, validated against them as P8 does) ---------------------------
def _registered_config() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA,
        "experiment_family": FAMILY,
        "spec_reference": SPEC,
        "frozen_source_sha256": FROZEN_SOURCE_DIGEST,
        "alphabet": {"bytes": list(ALPHABET), "size": ALPHABET_SIZE},
        "facts": {
            "identifier_length": IDENTIFIER_LENGTH,
            "free_symbols": FREE_SYMBOLS,
            "checksum_modulus": CHECKSUM_MODULUS,
            "answer_length": ANSWER_LENGTH,
            "cluster_size": CLUSTER_SIZE,
            "unseen_control_facts": UNSEEN_FACTS,
            "fixed_track_facts": FACTS_FIXED_TRACK,
            "proportional_facts": [FACTS_PROPORTIONAL[s] for s in SLOTS_BY_SIZE],
            "lane_d_facts_per_phase": LANE_D_FACTS,
        },
        "context": {
            "record_bytes": RECORD_BYTES,
            "records_per_context": RECORDS_PER_CONTEXT,
            "context_bytes": CONTEXT_BYTES,
            "input_length": INPUT_LENGTH,
            "targets_per_context": TARGETS_PER_CONTEXT,
            "answer_input_offset": ANSWER_INPUT_OFFSET,
            "answer_target_offset": ANSWER_TARGET_OFFSET,
            "knockout_positions": KNOCKOUT_POSITIONS,
            "batch_contexts": BATCH_CONTEXTS,
            "answer_sites_per_batch": ANSWER_SITES_PER_BATCH,
        },
        "templates": {
            "pool_size": TEMPLATE_POOL_SIZE,
            "pool": list(TEMPLATE_POOL),
            "pool_source_train_bytes_sha256": P1_TRAIN_SHA256,
            "pool_source_rows": CORPUS_TRAINED_ROWS,
            "train_bytes": 32,
            "held_out_bytes_each": 8,
            "held_out_combinations": 8,
        },
        "sizes": {
            "slots": list(SLOTS_BY_SIZE),
            "branches": [BRANCHES[s] for s in SLOTS_BY_SIZE],
            "per_branch": PER_BRANCH,
            "visit": VISIT,
            "top": TOP,
            "temperature": TEMPERATURE,
            "key_widths": list(KEY_WIDTHS),
            "value_width": VALUE_WIDTH,
            "hidden_width": HIDDEN_WIDTH,
            "gate_init": GATE_INIT,
            "init_std": INIT_STD,
            "soft_top": SOFT_TOP,
            "lane_d_slots": LANE_D_SLOTS,
        },
        "training": {
            "learning_rate": LEARNING_RATE,
            "weight_decay": WEIGHT_DECAY,
            "betas": list(BETAS),
            "eps": ADAM_EPS,
            "clip_norm": CLIP_NORM,
            "lazy_learning_rate": LAZY_LEARNING_RATE,
            "lazy_tables": list(LAZY_TABLES),
            "exposure_menu": list(EXPOSURE_MENU),
            "default_exposure": DEFAULT_EXPOSURE,
            "fixed_compute_facts": FIXED_COMPUTE_FACTS,
        },
        "objective": {
            "beta_soft": BETA_SOFT,
            "co_group": CO_GROUP,
            "alpha_u_doses": list(ALPHA_U_DOSES),
            "alpha_c_doses": list(ALPHA_C_DOSES),
            "alpha_c_with_alpha_u": ALPHA_C_WITH_ALPHA_U,
        },
        "gates": {
            "g2_alpha": G2_ALPHA,
            "g2_tests_primary": G2_TESTS_PRIMARY,
            "g2_tests_lane_d": G2_TESTS_LANE_D,
            "g1_tests_per_stream": G1_TESTS_PER_STREAM,
            "g1_permutations_per_test": G1_PERMUTATIONS_PER_TEST,
            "g1_p_threshold": G1_P_THRESHOLD,
            "g3_r2_accuracy": G3_R2_ACCURACY,
        },
        "support": {
            "p_absolute": SUPPORT_P_ABSOLUTE,
            "p_margin": SUPPORT_P_MARGIN,
            "specificity_other_slots": SPECIFICITY_OTHER_SLOTS,
            "specificity_delta": SPECIFICITY_DELTA,
            "specificity_share": SPECIFICITY_SHARE,
            "specificity_groups": SPECIFICITY_GROUPS,
            "specificity_group_tolerance": SPECIFICITY_GROUP_TOLERANCE,
        },
        "capacity": {
            "step_accuracy_min": STEP_ACCURACY_MIN,
            "step_ratio_b101": STEP_RATIO_B101,
            "step_ratio_b102": STEP_RATIO_B102,
            "not_supported_ratio": NOT_SUPPORTED_RATIO,
            "beats_dense_ratio": BEATS_DENSE_RATIO,
            "dependence_support_share": DEPENDENCE_SUPPORT_SHARE,
            "plateau_fraction": PLATEAU_FRACTION,
            "positive_accuracy_64k": POSITIVE_ACCURACY_64K,
            "empty_slot_rise": EMPTY_SLOT_RISE,
            "tree_ahead_ratio": TREE_AHEAD_RATIO,
            "tree_competitive_ratio": TREE_COMPETITIVE_RATIO,
            "ladder_material_bits": LADDER_MATERIAL_BITS,
        },
        "utilization": {
            "lane_b_min_accuracy": LANE_B_MIN_ACCURACY,
            "ustar_collapsed": UTIL_USTAR_COLLAPSED,
            "i_collapsed": UTIL_I_COLLAPSED,
            "eff_inflation": UTIL_EFF_INFLATION,
            "no_gain": UTIL_NO_GAIN,
            "improved": UTIL_IMPROVED,
            "support_length_max": UTIL_SUPPORT_LENGTH_MAX,
            "preserved": UTIL_PRESERVED,
            "accuracy_drop_max": UTIL_ACCURACY_DROP_MAX,
            "soft_usage_only_ratio": SOFT_USAGE_ONLY_RATIO,
            "regularizer_movement_ratio": REGULARIZER_MOVEMENT_RATIO,
        },
        "locality": {
            "cache_rhos_primary": list(CACHE_RHOS_PRIMARY),
            "cache_rows_primary": list(CACHE_ROWS_PRIMARY),
            "cache_rhos_sweep": list(CACHE_RHOS_SWEEP),
            "cache_rows_sweep": list(CACHE_ROWS_SWEEP),
            "null_replicates": NULL_REPLICATES,
            "e_null_floor": E_NULL_FLOOR,
            "e_ratio_positive": LOCALITY_E_RATIO_POSITIVE,
            "e_ratio_band": list(LOCALITY_E_RATIO_BAND),
            "quality_ratio": LOCALITY_QUALITY_RATIO,
            "tie_rules": list(TIE_RULES),
        },
        "lane_d": {
            "a0_min": LANE_D_A0_MIN,
            "no_new": LANE_D_NO_NEW,
            "forgetting": LANE_D_FORGETTING,
            "positive_b": LANE_D_POSITIVE_B,
            "positive_a": LANE_D_POSITIVE_A,
            "forgetting_gap": LANE_D_FORGETTING_GAP,
            "dense_forgetting_max": LANE_D_DENSE_FORGETTING_MAX,
        },
        "seeds": {
            "data": dict(DATA_SEEDS),
            "null_a": list(NULL_SEEDS_A),
            "null_b": list(NULL_SEEDS_B),
            "init": list(INIT_SEEDS),
            "primary_parent": list(PRIMARY_PARENT),
            "replicate_parent": list(REPLICATE_PARENT),
            "rehearsal_base": REHEARSAL_SEED_BASE,
        },
        "matrix": {
            "blocks": list(BLOCKS),
            "block_counts": dict(BLOCK_COUNTS),
            "total": TOTAL_CELLS,
        },
        "limits": {
            "rss_worker_bytes": RSS_WORKER_BYTES,
            "rss_aggregate_bytes": RSS_AGGREGATE_BYTES,
            "training_workers": list(TRAINING_WORKERS_RANGE),
            "simulation_workers": SIMULATION_WORKERS,
            "calibration_rehearsal_hours": CALIBRATION_REHEARSAL_HOURS,
        },
        "choices": dict(OPEN_CHOICES),
    }


def registered_config() -> dict[str, Any]:
    """The registered configuration derived from the constants of this module."""
    return _registered_config()


def validate_config(data: dict[str, Any]) -> dict[str, Any]:
    _validate(data, _registered_config(), "P9 config")
    return data


def load_config(path: Path | None = None) -> dict[str, Any]:
    with (path or repo_root() / DEFAULT_CONFIG).open("rb") as stream:
        return validate_config(tomllib.load(stream))


def _toml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, list):
        return "[" + ", ".join(_toml_value(v) for v in value) + "]"
    raise TypeError(f"cannot render {type(value).__name__} as TOML")


def _toml_lines(table: Mapping[str, Any], prefix: str) -> list[str]:
    lines = [f"{k} = {_toml_value(v)}" for k, v in table.items() if not isinstance(v, dict)]
    for key, value in table.items():
        if isinstance(value, dict):
            name = f"{prefix}.{key}" if prefix else key
            lines += ["", f"[{name}]", *_toml_lines(value, name)]
    return lines


def render_config_toml() -> str:
    """The canonical text of ``configs/p9_diagnostics.toml`` (tests require byte equality)."""
    header = [
        "# ADR-0017 P9 registered constants. Generated by studies.p9.core.render_config_toml and",
        "# validated against studies.p9.core; any difference is refused. [choices] lists the open",
        "# implementation choices made by the implementer (PENDING LEAD REVIEW).",
        "",
    ]
    return "\n".join([*header, *_toml_lines(_registered_config(), "")]) + "\n"


# --- record IO via arborlm.io -------------------------------------------------------------------------------
def write_record(path: Path, record: Mapping[str, Any]) -> None:
    """Atomically write a JSON record (canonical, no NaN) after checking its envelope keys."""
    if (
        record.get("study") != STUDY
        or record.get("schema") != SCHEMA
        or record.get("kind") not in RECORD_KINDS
    ):
        raise ValueError("P9 record needs study, schema and a registered kind")
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, dict(record))


def read_record(path: Path, kind: str | None = None) -> dict[str, Any]:
    record = read_json(path)
    if (
        not isinstance(record, dict)
        or record.get("study") != STUDY
        or record.get("schema") != SCHEMA
    ):
        raise ValueError(f"not a P9 record: {path}")
    if kind is not None and record.get("kind") != kind:
        raise ValueError(f"expected a {kind!r} record, got {record.get('kind')!r}: {path}")
    return record


def envelope(kind: str) -> dict[str, Any]:
    """``{"kind", "schema", "study"}`` to start every record with."""
    if kind not in RECORD_KINDS:
        raise ValueError(f"unknown record kind {kind!r}")
    return {"kind": kind, "schema": SCHEMA, "study": STUDY}


# --- cell directory layout (shared by train, evaluate, layout, sim, analysis) ----------------------------
def cell_dir(run_dir: Path, label: str) -> Path:
    """``<run>/cells/<label>``: ``train.json``, ``updates.jsonl``, ``snapshots/`` live here."""
    parse_label(label)
    return run_dir / "cells" / label


def snapshot_stem(update: int) -> str:
    return f"u{update:07d}"


def snapshot_dir(run_dir: Path, label: str, update: int) -> Path:
    """``<cell>/snapshots/u0000512``: ``model.pt``, ``optimizer.pt``, ``movement.pt``, ``snapshot.json``."""
    return cell_dir(run_dir, label) / "snapshots" / snapshot_stem(update)


def eval_path(run_dir: Path, label: str, update: int, stream: str) -> Path:
    """``<cell>/eval/u0000512/<stream>.json`` (an ``EvalRecord``)."""
    return cell_dir(run_dir, label) / "eval" / snapshot_stem(update) / f"{stream}.json"


def trace_path(run_dir: Path, label: str, update: int, stream: str, trace_kind: str) -> Path:
    """``<cell>/traces/u0000512/<stream>.<answer|all>.pt`` (a ``Trace`` written by ``write_trace``)."""
    return cell_dir(run_dir, label) / "traces" / snapshot_stem(update) / f"{stream}.{trace_kind}.pt"


def sim_path(run_dir: Path, label: str, update: int, stream: str) -> Path:
    """``<cell>/sim/u0000512/<stream>.json`` (a list of ``SimRecord`` under key ``records``)."""
    return cell_dir(run_dir, label) / "sim" / snapshot_stem(update) / f"{stream}.json"


# --- shared record schemas ---------------------------------------------------------------------------------
PARAM_GROUPS = (
    "keys_selected",  # keys selected at an answer site in the update
    "keys_candidate",  # keys that are top-64 candidates but unselected
    "keys_untouched",
    "values",
    "router",
    "projections",  # wq, wo, gate
    "dense",  # the dense adapter's matrices and gate
)
STREAM_NAMES = ("calibration", "panel_a", "panel_b", "h1", "h2", "mixed")
TRACE_KINDS = ("answer", "all")  # answer-site reads (primary) and all-position reads (secondary)


class UpdateRecord(TypedDict):
    """One line of ``<cell>/updates.jsonl`` (ADR 6.3). Per-group dicts are keyed by ``PARAM_GROUPS``."""

    update: int  # 1-based
    task_loss: float  # cross-entropy at answer sites only
    all_position_loss: float  # descriptive
    usage_penalty: float
    coaccess_penalty: float
    grad_norm_task: dict[str, float]
    grad_norm_usage: dict[str, float]
    grad_norm_coaccess: dict[str, float]
    param_change_norm: dict[str, float]
    clip_total_norm: float
    hinge_usage_active: bool
    hinge_coaccess_active: bool
    usage_entropy_soft: float | None
    usage_entropy_hard: float | None


class TrainRecord(TypedDict):
    """``<cell>/train.json`` (kind ``train``)."""

    kind: str
    schema: int
    study: str
    label: str
    index: int
    block: str
    mode: str  # registered | calibration | rehearsal
    exposure: int
    matched_updates: int
    run_updates: int
    snapshots: list[int]
    examples: int
    tokens: int
    unique_facts: int
    exposure_per_fact_min: int
    exposure_per_fact_max: int
    trainable_parameters: int
    stored_parameters: int
    initialized_slots: int
    optimizer_state_bytes: int
    lambda_u: float
    lambda_c: float
    wall_seconds: float
    peak_rss_bytes: int
    update_log: str
    snapshot_sha256: dict[str, str]  # str(update) -> sha256 of model.pt
    identity: Identity
    status: str  # completed | failed
    reason: str | None


class SnapshotRecord(TypedDict):
    """``<cell>/snapshots/uNNNNNNN/snapshot.json`` (kind ``snapshot``); tensors are in the siblings."""

    kind: str
    schema: int
    study: str
    label: str
    update: int
    model_sha256: str
    optimizer_sha256: str
    movement_sha256: (
        str  # movement.pt: key_with, key_without, value_with, value_without [N] float32
    )
    margin_8_9_quantiles: dict[str, float]
    soft_mass_outside_top8: float
    hinge_active: dict[str, bool]
    dead_slots: int
    keys_entered_top64_after_0: int


class EvalRecord(TypedDict):
    """``<cell>/eval/uNNNNNNN/<stream>.json`` (kind ``eval``): one snapshot on one stream/panel."""

    kind: str
    schema: int
    study: str
    label: str
    update: int
    stream: str  # a STREAM_NAMES entry, or "lane_d_<panel>_<set>"
    facts: int
    correct: int
    accuracy: float
    information_bits: float  # I_acc with the chance floor (ADR 6.1)
    logloss_gain_bits: float  # unfloored secondary
    mass_outside_alphabet_mean: float
    accuracy_with_neighbour: float | None
    accuracy_without_neighbour: float | None
    unseen_correct: int
    unseen_facts: int
    leakage: bool
    value_permuted_accuracy: float | None
    disabled_accuracy: float | None
    useful_slots: int | None  # U*
    ustar_interpretable: bool | None
    specificity: dict[str, Any]
    mean_support_length: float | None
    share_correct_with_support: float | None
    share_stay_correct_without_site_read: float | None
    usage: dict[str, Any]  # distinct, entropy-effective (hard and soft), hot-64 share, dead, ...
    per_fact_file: str | None  # median and full per-fact distribution
    identity: Identity


class SimRecord(TypedDict):
    """One simulated setting (kind ``sim``); a file holds ``{"records": [SimRecord, ...]}``."""

    kind: str
    schema: int
    study: str
    label: str
    update: int
    stream: str  # panel_a | panel_b
    trace_kind: str  # TRACE_KINDS
    layout: str
    rows_per_page: int
    cache_fraction: float
    cache_pages: int
    working_set: int
    tie: str
    actual_misses: int
    null_misses: list[int]  # three count-preserving nulls
    null_miss_rate: float
    e_ratio: float | None  # actual misses / mean null misses
    degenerate: bool
    pages_per_query: float
    cross_query_reuse: float
    identity: Identity


class TaskRecord(TypedDict):
    label: str
    task_id: str  # immutable: sha256 of (stage, label, identity)
    status: str  # completed | failed | killed_rss | killed_cap | not_started | skipped_dependency
    returncode: int | None
    seconds: float
    peak_rss_bytes: int
    reason: str | None
    depends_on: list[str]
    result_path: str | None
    result_sha256: str | None


class StageManifest(TypedDict):
    """``<run>/manifest.json`` (kind ``stage_manifest``): one per stage run."""

    kind: str
    schema: int
    study: str
    stage: str
    run_id: str
    mode: str
    started_utc: str
    finished_utc: str | None
    identity: Identity
    workers: int
    caps: dict[str, float]
    tasks: list[TaskRecord]
    status: str  # COMPLETE | INCOMPLETE | ENGINEERING_FAIL
    skipped_for_dependency: list[str]


class CalibrationRecord(TypedDict):
    """Calibration output (kind ``calibration``, ADR 12 step 4; rehearsal seeds only)."""

    kind: str
    schema: int
    study: str
    seeds: dict[str, int]
    r2_accuracy: dict[str, dict[str, float]]  # str(slots) -> str(E) -> accuracy
    probes: dict[str, Any]
    attainable_probability: dict[str, float]
    selected_exposure: int | None
    task_ceiling_fail: list[int]
    identity: Identity


# --- the trace file (layout.py and sim.py read it; evaluate.py writes it) -------------------------------------
@dataclass
class Trace:
    """Memory reads of one snapshot on one stream, one row per query in (context, position) order.

    ``selected [Q, 8] int64`` selected slot ids; ``branches [Q, 2] int64`` visited branches (tree
    only, else None); ``context [Q]``, ``position [Q]`` (input position 0..62), ``fact [Q]`` (the fact
    id of record ``position // 8``) and ``cluster [Q]`` (-1 for unseen facts) all int64. An answer-site
    trace has queries only at positions 8r+6; an all-position trace has all 63 positions.
    """

    label: str
    update: int
    stream: str
    kind: str  # TRACE_KINDS
    slots: int
    selected: "Tensor"
    branches: "Tensor | None"
    context: "Tensor"
    position: "Tensor"
    fact: "Tensor"
    cluster: "Tensor"


def write_trace(path: Path, trace: Trace) -> str:
    """Write ``trace`` with ``torch.save`` (as ``arborlm.checkpoint`` does) and return the file's SHA-256."""
    import torch

    if trace.kind not in TRACE_KINDS:
        raise ValueError("unknown trace kind")
    payload: dict[str, Any] = {
        "label": trace.label,
        "update": trace.update,
        "stream": trace.stream,
        "kind": trace.kind,
        "slots": trace.slots,
        "selected": trace.selected.to(torch.int64).contiguous(),
        "context": trace.context.to(torch.int64).contiguous(),
        "position": trace.position.to(torch.int64).contiguous(),
        "fact": trace.fact.to(torch.int64).contiguous(),
        "cluster": trace.cluster.to(torch.int64).contiguous(),
    }
    if trace.branches is not None:
        payload["branches"] = trace.branches.to(torch.int64).contiguous()
    path.parent.mkdir(parents=True, exist_ok=True)
    import io

    buffer = io.BytesIO()
    torch.save(payload, buffer)
    from arborlm.io import atomic_write

    atomic_write(path, buffer.getvalue())
    return file_sha256(path)


def read_trace(path: Path, expected_sha256: str | None = None) -> Trace:
    import torch

    if expected_sha256 is not None and file_sha256(path) != expected_sha256:
        raise ValueError(f"trace hash mismatch: {path}")
    with path.open("rb") as stream:
        payload = torch.load(stream, map_location="cpu", weights_only=True)
    return Trace(
        label=payload["label"],
        update=int(payload["update"]),
        stream=payload["stream"],
        kind=payload["kind"],
        slots=int(payload["slots"]),
        selected=payload["selected"],
        branches=payload.get("branches"),
        context=payload["context"],
        position=payload["position"],
        fact=payload["fact"],
        cluster=payload["cluster"],
    )


# --- analysis-side shared types (analysis_a..d and report read these) -------------------------------------
PANELS = ("A", "B")
PANEL_STREAM = {"A": "panel_a", "B": "panel_b"}
NOT_REPLICATED, NOT_EVALUATED, INTERMEDIATE = "NOT REPLICATED", "NOT_EVALUATED", "INTERMEDIATE"
EvalKey = tuple[str, int, str]  # (cell label, snapshot update, stream name)
EvalIndex = Mapping[EvalKey, EvalRecord]


class ClassResult(TypedDict):
    """The outcome of one class rule for one subject (an architecture, a cell, or an arm).

    ``cls`` is the final class after the panel-agreement rule; ``panel_classes`` holds the class each
    primary panel would give alone (NOT REPLICATED when they differ); ``annotations`` are printed with
    the class and never change it; ``details`` holds every number the rule used, with its
    median and per-fact distribution reference where ADR 6.3 requires one."""

    lane: str
    subject: str
    cls: str
    panel_classes: dict[str, str]
    annotations: list[str]
    details: dict[str, Any]


def labels_of(items: Iterable[Cell]) -> list[str]:
    return [c.label for c in items]


def sequence_hash(values: Sequence[int]) -> str:
    return sha256(canonical_json(list(values)))
