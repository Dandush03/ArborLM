# ruff: noqa: E501
"""P9I shared contract: constants of ADR-0017 Part I (section 18), the 57-cell registry, seeds, the
update-count rule of section I.6, thresholds of sections I.6 and I.8, config, identity hashes, record IO
and the charged-time ledger of the 4-hour cap.

Specification: ``docs/decisions/ADR-0017-parallel-capacity-and-locality-diagnostics.md`` section 18 and
15.3. Human decision 1 of Part I (implementation, calibration on rehearsal draw 1, rehearsal) is
recorded; the registered run is not approved by this code existing. Every number below is copied from
the ADR. Nothing here trains or evaluates a model.

Status: implementation self-checked only. Not independent review, not Astra validation, not human
approval.
"""

import hashlib
import json
import math
import re
import tomllib
import uuid
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NamedTuple, TypedDict

from arborlm.config import _validate
from arborlm.io import canonical_json, file_sha256, read_json, sha256, write_json
from studies.p9 import core as p9core

# --- identity of the study ---------------------------------------------------------------------
SPEC = p9core.SPEC
STUDY = "P9I"
FAMILY = "P9I_QUERY_INTERFACE_PREREQUISITE"
SCHEMA = 1
DEFAULT_CONFIG = Path("configs/p9i_interface.toml")

# P9 modules whose code Part I imports and runs; hashed into the source digest (a test scans the p9i
# sources and fails when a studies.p9 module is imported that is not listed).
IMPORTED_P9_MODULES = (
    "__init__",
    "controls",
    "core",
    "data",
    "evaluate",
    "model",
    "objective",
    "pool",
    "train",
)

# --- the task (imported from P9, section 4 of the ADR; re-exported so Part I code has one namespace) -
ALPHABET = p9core.ALPHABET
ALPHABET_SIZE = p9core.ALPHABET_SIZE
ALPHABET_BASE = ALPHABET[0]
CONTEXT_BYTES, INPUT_LENGTH = p9core.CONTEXT_BYTES, p9core.INPUT_LENGTH
RECORD_BYTES, RECORDS_PER_CONTEXT = p9core.RECORD_BYTES, p9core.RECORDS_PER_CONTEXT
ANSWER_SITES_PER_CONTEXT = p9core.ANSWER_SITES_PER_CONTEXT
ANSWER_SITE_POSITIONS = p9core.ANSWER_SITE_POSITIONS
BATCH_CONTEXTS = p9core.BATCH_CONTEXTS
ANSWER_SITES_PER_BATCH = p9core.ANSWER_SITES_PER_BATCH
SLOTS_BY_SIZE = p9core.SLOTS_BY_SIZE  # 4,096 / 16,384 / 65,536
FACTS_PROPORTIONAL = p9core.FACTS_PROPORTIONAL
KEY_WIDTH, TOP, TEMPERATURE = p9core.KEY_WIDTH, p9core.TOP, p9core.TEMPERATURE
HIDDEN_WIDTH = p9core.HIDDEN_WIDTH
CHANCE = p9core.CHANCE

# --- interfaces (section I.3) -----------------------------------------------------------------------
WINDOW = 7  # positions t-6 .. t
HEADS, HEAD_WIDTH = 4, 8
W_EXTRA = KEY_WIDTH * HIDDEN_WIDTH * (WINDOW - 1)  # 16 * 224 - 16 * 32 = 3,072
A_EXTRA = 3 * HIDDEN_WIDTH * HIDDEN_WIDTH  # 3,072
BB_PARAMETERS = 4224  # block-0 qkv (96 x 32 + 96) and output projection (32 x 32 + 32)
D7_TOLERANCE = 0.001  # "within 0.1%"
D7_HIDDEN_EXPECTED: dict[int, int] = {4096: 786, 16384: 3090, 65536: 12306}

ARMS = ("N", "W7", "E7", "A4", "A4E", "R1", "R2", "D", "D7", "BB", "BB-D", "BB-0")
INTERFACE_ARMS = ("N", "W7", "E7", "A4", "A4E")
ORACLE_ARMS = ("R1", "R2")
DENSE_ARMS = ("D", "D7", "BB-D")
BB_ARMS = ("BB", "BB-D", "BB-0")
MEMORY_ARMS = ("N", "W7", "E7", "A4", "A4E", "R1", "R2", "BB")  # a key/value table exists
CLASSIFIED_ARMS = ("W7", "A4", "BB")  # classified for the selection; E7, A4E, N the same way for the record
RECORD_CLASSIFIED_ARMS = ("N", "W7", "E7", "A4", "A4E", "BB")
LEARNING_RATE, CLIP_NORM = p9core.LEARNING_RATE, p9core.CLIP_NORM

# --- calibration, updates and snapshots (section I.6) ------------------------------------------------
CANDIDATE_UPDATES = (2048, 4096, 8192, 16384)
CALIBRATION_SNAPSHOTS = (1024, 2048, 4096, 8192, 16384)
CALIBRATION_ARMS = ("R1", "R2")
CALIBRATION_DRAW = 1
REHEARSAL_MAX_DRAW = 9
CALIBRATION_INIT_SEEDS = (1791, 1792)
INIT_SEEDS = (1801, 1802)
REGISTERED_DATA_SEED_BASE = 182001
TEST_SEED_BASE = 900001
PRIMARY_PARENT, REPLICATE_PARENT = p9core.PRIMARY_PARENT, p9core.REPLICATE_PARENT
R2_MIN_ACCURACY, R1_MIN_ACCURACY = 0.95, 0.90
TASK_CEILING_FAIL, ORACLE_QUERY_FAIL = "TASK_CEILING_FAIL", "ORACLE_QUERY_FAIL"
NOT_JOINT = "NOT_JOINT"  # no U qualifies for both rungs although each is reached alone; not named by the ADR

# --- classes (section I.8) ----------------------------------------------------------------------------
WORKS_ACCURACY, WORKS_ETA = 0.5, 0.90
PARTIAL_ACCURACY = 0.25
R1_NOT_EVALUATED = 0.5
BEATS_DENSE_RATIO = 1.10
BACKBONE_HURTS, BACKBONE_NOTHING = 1.03, 0.97
LM_DEGRADED_RELATIVE = 0.05
NEAREST_QUERY_COSINE = 0.9

# --- resources (section I.10, decision 15.3) ------------------------------------------------------------
RSS_WORKER_BYTES = p9core.RSS_WORKER_BYTES  # 3 GiB
RSS_AGGREGATE_BYTES = p9core.RSS_AGGREGATE_BYTES  # 24 GiB
CAP_HOURS = 4.0
CAP_SECONDS = CAP_HOURS * 3600.0
WORKERS = 6  # single-thread workers, six at a time

# --- run directories and records ---------------------------------------------------------------------------
STAGE_CODES: dict[str, str] = {
    "generate": "P",
    "calibrate": "C",
    "rehearse": "H",
    "gates": "G",
    "train": "T",
    "evaluate": "E",
    "analyze": "A",
    "report": "R",
    "dry": "D",
}
RECORD_KINDS = (
    "train",
    "snapshot",
    "eval",
    "stage_manifest",
    "calibration",
    "rehearsal",
    "analysis",
    "data_manifest",
    "gates",
)
PANELS = ("A", "B")
PANEL_STREAM = {"A": "panel_a", "B": "panel_b"}
SECONDARY_STREAMS = ("h1", "h2", "mixed")


# --- the cells (section I.7) ------------------------------------------------------------------------
@dataclass(frozen=True)
class Cell:
    """One cell. ``block`` is ``core``, ``BB`` or ``CAL`` (calibration); ``group`` names the row of the
    section I.7 table (used for the asserted counts)."""

    block: str
    group: str
    arm: str
    slots: int
    parent: tuple[int, int]
    seed: int
    label: str

    def __post_init__(self) -> None:
        init_seeds = CALIBRATION_INIT_SEEDS if self.block == "CAL" else INIT_SEEDS
        if (
            self.block not in ("core", "BB", "CAL")
            or self.arm not in ARMS
            or self.slots not in SLOTS_BY_SIZE
            or self.parent not in (PRIMARY_PARENT, REPLICATE_PARENT)
            or self.seed not in init_seeds
            or (self.block == "BB") != (self.arm in BB_ARMS)
            or (self.block == "CAL" and self.arm not in CALIBRATION_ARMS)
        ):
            raise ValueError(f"unregistered P9I cell: {self.label}")

    @property
    def facts(self) -> int:
        return FACTS_PROPORTIONAL[self.slots]

    @property
    def backbone(self) -> int:
        return self.parent[0]

    @property
    def order(self) -> int:
        return self.parent[1]

    @property
    def replicate(self) -> bool:
        return self.parent == REPLICATE_PARENT


def make_label(arm: str, slots: int, parent: tuple[int, int], seed: int, prefix: str = "") -> str:
    return f"{prefix}{arm}-n{slots}-b{parent[0]}-o{parent[1]}-s{seed}"


def _cell(block: str, group: str, arm: str, slots: int, parent: tuple[int, int], seed: int) -> Cell:
    prefix = "CAL-" if block == "CAL" else ""
    return Cell(block, group, arm, slots, parent, seed, make_label(arm, slots, parent, seed, prefix))


ROW_COUNTS: dict[str, int] = {
    "core-16384": 22,
    "core-65536": 10,
    "core-4096": 8,
    "bb-wide": 13,
    "bb-4096": 4,
}
CORE_TOTAL, BB_TOTAL, TOTAL_CELLS = 40, 17, 57
_CORE_ARMS: dict[int, tuple[str, ...]] = {
    16384: ("N", "W7", "E7", "A4", "A4E", "R1", "R2", "D", "D7"),
    65536: ("N", "W7", "A4", "R1", "D7"),
    4096: ("N", "W7", "A4", "R1"),
}
_REPLICATE_ARMS_16K = ("W7", "A4", "R1", "D7")


def _build_cells() -> list[Cell]:
    out: list[Cell] = []
    for slots in (16384, 65536, 4096):
        group = f"core-{slots}"
        for arm in _CORE_ARMS[slots]:
            for seed in INIT_SEEDS:
                out.append(_cell("core", group, arm, slots, PRIMARY_PARENT, seed))
        if slots == 16384:
            for arm in _REPLICATE_ARMS_16K:
                out.append(_cell("core", group, arm, slots, REPLICATE_PARENT, INIT_SEEDS[0]))
    for slots in (16384, 65536):
        for arm in BB_ARMS:
            for seed in INIT_SEEDS:
                out.append(_cell("BB", "bb-wide", arm, slots, PRIMARY_PARENT, seed))
    out.append(_cell("BB", "bb-wide", "BB", 16384, REPLICATE_PARENT, INIT_SEEDS[0]))
    for arm in ("BB", "BB-0"):
        for seed in INIT_SEEDS:
            out.append(_cell("BB", "bb-4096", arm, 4096, PRIMARY_PARENT, seed))
    return out


_CELLS: list[Cell] = _build_cells()
_BY_LABEL: dict[str, Cell] = {c.label: c for c in _CELLS}


def _assert_registry(cells: Sequence[Cell]) -> None:
    counts: dict[str, int] = {}
    for c in cells:
        counts[c.group] = counts.get(c.group, 0) + 1
    if counts != ROW_COUNTS:
        raise ImportError(f"P9I registry rows differ from section I.7: {counts}")
    core_n = sum(1 for c in cells if c.block == "core")
    bb_n = sum(1 for c in cells if c.block == "BB")
    if (core_n, bb_n, len(cells)) != (CORE_TOTAL, BB_TOTAL, TOTAL_CELLS):
        raise ImportError("P9I registry totals differ from section I.7")
    if len(_BY_LABEL) != len(cells):
        raise ImportError("P9I cell labels are not unique")


_assert_registry(_CELLS)


def cells() -> list[Cell]:
    """The 57 registered cells in registry order."""
    return list(_CELLS)


def cells_of_group(group: str) -> list[Cell]:
    return [c for c in _CELLS if c.group == group]


def calibration_cells() -> list[Cell]:
    """The 18 calibration runs: R1 and R2 at the three sizes; seeds 1791 and 1792 on B101/O301 and 1791
    on B102/O302 (section I.6)."""
    out: list[Cell] = []
    for arm in CALIBRATION_ARMS:
        for slots in SLOTS_BY_SIZE:
            for seed in CALIBRATION_INIT_SEEDS:
                out.append(_cell("CAL", "cal", arm, slots, PRIMARY_PARENT, seed))
            out.append(_cell("CAL", "cal", arm, slots, REPLICATE_PARENT, CALIBRATION_INIT_SEEDS[0]))
    return out


_CAL_BY_LABEL: dict[str, Cell] = {c.label: c for c in calibration_cells()}


_TEST_LABEL = re.compile(r"^TEST-(?P<arm>[A-Z0-9-]+?)-n(?P<slots>\d+)-b(?P<b>\d+)-o(?P<o>\d+)-s(?P<seed>\d+)$")


def parse_label(label: str) -> Cell:
    """The registered or calibration cell named ``label``; labels of the form ``TEST-<arm>-n<slots>-...``
    (``make_cell``: unit tests and the DRY stage) are rebuilt from their parts. ValueError otherwise."""
    cell = _BY_LABEL.get(label) or _CAL_BY_LABEL.get(label)
    if cell is None:
        match = _TEST_LABEL.match(label)
        if match is None:
            raise ValueError(f"unknown P9I cell label {label!r}")
        cell = make_cell(match["arm"], int(match["slots"]), (int(match["b"]), int(match["o"])), int(match["seed"]))
    return cell


# --- parameter counts (analytical; the model module reports the measured ones) ----------------------------
def memory_parameters(slots: int) -> int:
    """Trainable parameters of arm N (flat memory, key width 16): P9's count."""
    return p9core.memory_parameters("flat", slots)


def w7_parameters(slots: int) -> int:
    """Arm W7 including the interface: N + 3,072."""
    return memory_parameters(slots) + W_EXTRA


def d7_parameters(hidden: int) -> int:
    """Dense adapter on the 224-wide window: w1 [h, 224], w2 [32, h], gate."""
    return hidden * HIDDEN_WIDTH * WINDOW + HIDDEN_WIDTH * hidden + 1


def d7_hidden_width(slots: int) -> int:
    """The hidden width whose parameter count is closest to arm W7's (section I.3.3: "within 0.1%";
    expected 786 / 3,090 / 12,306)."""
    target = w7_parameters(slots)
    width = round((target - 1) / (HIDDEN_WIDTH * (WINDOW + 1)))
    best = min(range(max(1, width - 2), width + 3), key=lambda h: abs(d7_parameters(h) - target))
    if abs(d7_parameters(best) - target) > D7_TOLERANCE * target:
        raise ValueError("no dense width matches W7 within 0.1%")
    return best


def dense_plain_hidden_width(slots: int) -> int:
    """D plain: matched to arm N exactly as P9 (``core.dense_hidden_width``)."""
    return p9core.dense_hidden_width(slots)


# --- seeds ---------------------------------------------------------------------------------------------------
def registered_seeds() -> p9core.SeedSet:
    """Registered data seeds 182001 upward (one per P9 data-seed name, in P9's order). Part I owns this
    range; ADR-0017's registered seeds stay unused."""
    names = list(p9core.DATA_SEEDS)
    values = {name: REGISTERED_DATA_SEED_BASE + i for i, name in enumerate(names)}
    top = REGISTERED_DATA_SEED_BASE + len(names)
    return p9core.SeedSet(
        "p9i-registered",
        **values,
        null_seeds_a=tuple(top + i for i in range(3)),
        null_seeds_b=tuple(top + 3 + i for i in range(3)),
    )


def registered_seed_values() -> frozenset[int]:
    s = registered_seeds()
    return frozenset([*s.data_values(), *s.null_seeds_a, *s.null_seeds_b])


def test_seeds(offset: int = 0) -> p9core.SeedSet:
    """Seeds for unit tests: 900001 upward, disjoint from every other range."""
    names = list(p9core.DATA_SEEDS)
    base = TEST_SEED_BASE + 100 * offset
    values = {name: base + i for i, name in enumerate(names)}
    return p9core.SeedSet(
        f"p9i-test-{offset}",
        **values,
        null_seeds_a=tuple(base + 20 + i for i in range(3)),
        null_seeds_b=tuple(base + 30 + i for i in range(3)),
    )


def rehearsal_draw_seeds(draw: int) -> p9core.SeedSet:
    """Rehearsal-namespace draw ``draw`` (P9's namespace, 179001 + 100 k upward), limited to k <= 9. The
    calibration draw (1) is only used by ``calibration_seeds``."""
    if not 0 <= draw <= REHEARSAL_MAX_DRAW:
        raise ValueError(f"rehearsal draws are limited to 0..{REHEARSAL_MAX_DRAW}")
    return p9core.rehearsal_seeds(draw)


def calibration_seeds() -> p9core.SeedSet:
    """Rehearsal draw 1 (data seeds 179101 upward): the calibration data (section I.6)."""
    return p9core.rehearsal_seeds(CALIBRATION_DRAW)


def seed_namespaces() -> dict[str, frozenset[int]]:
    """Every seed range Part I touches, by name (the disjointness test and G1's seed check read it)."""
    def values(s: p9core.SeedSet) -> frozenset[int]:
        return frozenset([*s.data_values(), *s.null_seeds_a, *s.null_seeds_b])

    return {
        "registered_data": registered_seed_values(),
        "registered_init": frozenset(INIT_SEEDS),
        "calibration_init": frozenset(CALIBRATION_INIT_SEEDS),
        "calibration_data": values(calibration_seeds()),
        "rehearsal_data": frozenset().union(
            *(values(p9core.rehearsal_seeds(k)) for k in range(REHEARSAL_MAX_DRAW + 1) if k != CALIBRATION_DRAW)
        ),
        "test": frozenset().union(*(values(test_seeds(k)) for k in range(3))),
        "p9_registered": p9core.registered_seed_values(),
    }


def init_seed_of(cell: Cell, mode: str, seeds: p9core.SeedSet) -> int:
    """Initialization seed: the cell's own in the registered run and the calibration; in a rehearsal the
    rehearsal facts seed plus the cell's offset (so the two seeds still differ and no registered
    initialization seed is used)."""
    if mode == "rehearsal":
        return seeds.facts + (cell.seed - INIT_SEEDS[0])
    return cell.seed


# --- the update-count rule of section I.6 ---------------------------------------------------------------
class UpdateSelection(NamedTuple):
    """``updates`` is U, or None when no U qualifies at the live sizes; ``failed`` maps a failed size to
    the labels (``TASK_CEILING_FAIL`` for R2, ``ORACLE_QUERY_FAIL`` for R1, ``NOT_JOINT`` when each
    rung is reached at some U but never both at the same U); ``live`` the sizes that remain."""

    updates: int | None
    failed: dict[int, list[str]]
    live: list[int]


def select_updates(
    r2: Mapping[int, Mapping[int, float]],
    r1: Mapping[int, Mapping[int, float]],
    candidates: Sequence[int] = CANDIDATE_UPDATES,
) -> UpdateSelection:
    """Section I.6 rule. ``r2[size][U]`` and ``r1[size][U]`` are the accuracy at U updates already taken
    as the minimum over the two B101 calibration runs and both panels. U is the smallest of
    ``candidates`` (default ``CANDIDATE_UPDATES``; the DRY stage passes tiny ones) at which, at every size, R2 >= 0.95 and R1 >= 0.90. A size at which no U
    qualifies is failed (R2 never reaching 0.95: TASK_CEILING_FAIL; R1 never reaching 0.90:
    ORACLE_QUERY_FAIL; both may apply) and is not run; U is then the smallest value qualifying at the
    remaining sizes."""
    sizes = sorted(set(r2) | set(r1))
    failed: dict[int, list[str]] = {}
    for size in sizes:
        ok2 = {u for u in candidates if r2.get(size, {}).get(u, -math.inf) >= R2_MIN_ACCURACY}
        ok1 = {u for u in candidates if r1.get(size, {}).get(u, -math.inf) >= R1_MIN_ACCURACY}
        if ok1 & ok2:
            continue
        labels = []
        if not ok2:
            labels.append(TASK_CEILING_FAIL)
        if not ok1:
            labels.append(ORACLE_QUERY_FAIL)
        failed[size] = labels or [NOT_JOINT]
    live = [s for s in sizes if s not in failed]
    chosen: int | None = None
    for u in candidates:
        if live and all(
            r2.get(s, {}).get(u, -math.inf) >= R2_MIN_ACCURACY
            and r1.get(s, {}).get(u, -math.inf) >= R1_MIN_ACCURACY
            for s in live
        ):
            chosen = u
            break
    return UpdateSelection(chosen, failed, live)


# --- config ---------------------------------------------------------------------------------------------------
def registered_config() -> dict[str, Any]:
    """The configuration mirrored in ``configs/p9i_interface.toml`` (derived from the constants)."""
    return {
        "schema_version": SCHEMA,
        "experiment_family": FAMILY,
        "spec_reference": SPEC,
        "alphabet": {"bytes": list(ALPHABET), "size": ALPHABET_SIZE},
        "memory": {
            "key_width": KEY_WIDTH,
            "top": TOP,
            "temperature": TEMPERATURE,
            "slots": list(SLOTS_BY_SIZE),
            "facts": [FACTS_PROPORTIONAL[s] for s in SLOTS_BY_SIZE],
        },
        "interfaces": {
            "window": WINDOW,
            "heads": HEADS,
            "head_width": HEAD_WIDTH,
            "w_extra_parameters": W_EXTRA,
            "a_extra_parameters": A_EXTRA,
            "bb_parameters": BB_PARAMETERS,
            "d7_hidden_widths": [D7_HIDDEN_EXPECTED[s] for s in SLOTS_BY_SIZE],
            "d7_tolerance": D7_TOLERANCE,
            "arms": list(ARMS),
        },
        "training": {
            "learning_rate": LEARNING_RATE,
            "clip_norm": CLIP_NORM,
            "batch_contexts": BATCH_CONTEXTS,
            "loss": "alphabet cross-entropy at answer sites (32 symbols 0x40-0x5F)",
            "candidate_updates": list(CANDIDATE_UPDATES),
        },
        "calibration": {
            "draw": CALIBRATION_DRAW,
            "init_seeds": list(CALIBRATION_INIT_SEEDS),
            "snapshots": list(CALIBRATION_SNAPSHOTS),
            "r2_min_accuracy": R2_MIN_ACCURACY,
            "r1_min_accuracy": R1_MIN_ACCURACY,
            "rehearsal_max_draw": REHEARSAL_MAX_DRAW,
        },
        "seeds": {
            "registered_data_base": REGISTERED_DATA_SEED_BASE,
            "init": list(INIT_SEEDS),
            "test_base": TEST_SEED_BASE,
        },
        "matrix": {
            "rows": dict(ROW_COUNTS),
            "core_total": CORE_TOTAL,
            "bb_total": BB_TOTAL,
            "total": TOTAL_CELLS,
        },
        "thresholds": {
            "works_accuracy": WORKS_ACCURACY,
            "works_eta": WORKS_ETA,
            "partial_accuracy": PARTIAL_ACCURACY,
            "r1_not_evaluated": R1_NOT_EVALUATED,
            "beats_dense_ratio": BEATS_DENSE_RATIO,
            "backbone_hurts": BACKBONE_HURTS,
            "backbone_nothing": BACKBONE_NOTHING,
            "lm_degraded_relative": LM_DEGRADED_RELATIVE,
            "nearest_query_cosine": NEAREST_QUERY_COSINE,
        },
        "resources": {
            "rss_worker_bytes": RSS_WORKER_BYTES,
            "rss_aggregate_bytes": RSS_AGGREGATE_BYTES,
            "cap_hours": CAP_HOURS,
            "workers": WORKERS,
        },
    }


def validate_config(data: dict[str, Any]) -> dict[str, Any]:
    _validate(data, registered_config(), "P9I config")
    return data


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


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
    """The canonical text of ``configs/p9i_interface.toml`` (a test requires byte equality)."""
    header = [
        "# ADR-0017 Part I (P9I) registered constants. Generated by studies.p9i.core.render_config_toml",
        "# and validated against studies.p9i.core; any difference is refused.",
        "",
    ]
    return "\n".join([*header, *_toml_lines(registered_config(), "")]) + "\n"


# --- identity hashes -------------------------------------------------------------------------------------------
def source_hashes(root: Path | None = None) -> dict[str, str]:
    """SHA-256 of every ``studies/p9i/*.py`` and of the imported ``studies/p9/*.py`` modules."""
    base = root or repo_root()
    out: dict[str, str] = {}
    for p in sorted((base / "studies" / "p9i").glob("*.py")):
        out[f"studies/p9i/{p.name}"] = file_sha256(p)
    for name in IMPORTED_P9_MODULES:
        p = base / "studies" / "p9" / f"{name}.py"
        out[f"studies/p9/{name}.py"] = file_sha256(p)
    return out


def source_digest(root: Path | None = None) -> str:
    return sha256(canonical_json(source_hashes(root)))


def spec_sha256(root: Path | None = None) -> str:
    return file_sha256((root or repo_root()) / SPEC)


def config_sha256(path: Path | None = None) -> str:
    return sha256(canonical_json(load_config(path)))


class Identity(TypedDict):
    source_sha256: str  # studies/p9i/*.py and the imported studies/p9/*.py
    spec_sha256: str  # the ADR file
    config_sha256: str
    frozen_source_sha256: str  # arborlm.p8_core.source_digest()


def code_identity(root: Path | None = None) -> Identity:
    from arborlm import p8_core

    base = root or repo_root()
    return Identity(
        source_sha256=source_digest(base),
        spec_sha256=spec_sha256(base),
        config_sha256=config_sha256(base / DEFAULT_CONFIG),
        frozen_source_sha256=p8_core.source_digest(),
    )


# --- run names, records and paths -------------------------------------------------------------------------------
def utc_stamp(now: datetime | None = None) -> str:
    return (now or datetime.now(UTC)).strftime("%Y%m%dT%H%M%S%fZ")


def run_name(stage: str, now: datetime | None = None, unique: str | None = None) -> str:
    """``P9I<code>-<utc>-<uuid hex>`` for a stage in ``STAGE_CODES``."""
    if stage not in STAGE_CODES:
        raise ValueError(f"unknown P9I stage {stage!r}")
    return f"P9I{STAGE_CODES[stage]}-{utc_stamp(now)}-{unique or uuid.uuid4().hex}"


def parse_run_name(name: str) -> tuple[str, str, str]:
    head, _, rest = name.partition("-")
    stamp, _, unique = rest.partition("-")
    codes = {code: stage for stage, code in STAGE_CODES.items()}
    if not head.startswith("P9I") or head[3:] not in codes or not stamp.endswith("Z") or not unique:
        raise ValueError(f"not a P9I run name: {name!r}")
    return codes[head[3:]], stamp, unique


def envelope(kind: str) -> dict[str, Any]:
    if kind not in RECORD_KINDS:
        raise ValueError(f"unknown record kind {kind!r}")
    return {"kind": kind, "schema": SCHEMA, "study": STUDY}


def write_record(path: Path, record: Mapping[str, Any]) -> None:
    """Atomically write a JSON record (canonical, no NaN) after checking its envelope keys."""
    if (
        record.get("study") != STUDY
        or record.get("schema") != SCHEMA
        or record.get("kind") not in RECORD_KINDS
    ):
        raise ValueError("P9I record needs study, schema and a registered kind")
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, dict(record))


def read_record(path: Path, kind: str | None = None) -> dict[str, Any]:
    record = read_json(path)
    if not isinstance(record, dict) or record.get("study") != STUDY or record.get("schema") != SCHEMA:
        raise ValueError(f"not a P9I record: {path}")
    if kind is not None and record.get("kind") != kind:
        raise ValueError(f"expected a {kind!r} record, got {record.get('kind')!r}: {path}")
    return record


def cell_dir(run_dir: Path, label: str) -> Path:
    parse_label(label)
    return run_dir / "cells" / label


def snapshot_stem(update: int) -> str:
    return f"u{update:07d}"


def snapshot_dir(run_dir: Path, label: str, update: int) -> Path:
    return cell_dir(run_dir, label) / "snapshots" / snapshot_stem(update)


def eval_path(run_dir: Path, label: str, update: int, stream: str) -> Path:
    return cell_dir(run_dir, label) / "eval" / snapshot_stem(update) / f"{stream}.json"


def default_experiments_root() -> Path:
    return p9core.default_experiments_root()


# --- the charged-time ledger of the 4-hour cap ----------------------------------------------------------------
class LedgerRefused(RuntimeError):
    """A stage cannot start: the remainder of the cap is smaller than the stage's own cap."""


class Ledger:
    """Charged wall time of calibration, rehearsal and the run together (section I.10, decision 15.3).
    Entries are appended to one JSON file; nothing is ever removed. A stage refuses to start when the
    remainder of the cap is smaller than its own stage cap, and is charged what it used."""

    def __init__(self, path: Path, cap_seconds: float = CAP_SECONDS) -> None:
        self.path = path
        self.cap_seconds = cap_seconds

    def entries(self) -> list[dict[str, Any]]:
        if not self.path.is_file():
            return []
        data = read_json(self.path)
        if not isinstance(data, dict) or data.get("study") != STUDY:
            raise ValueError(f"not a P9I ledger: {self.path}")
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
                f"stage {stage}: {self.remaining():.0f} s of the {self.cap_seconds:.0f} s cap remain, "
                f"less than the stage cap of {stage_cap_seconds:.0f} s; the work stops and returns to the human lead"
            )

    def charge(self, stage: str, run: str, seconds: float) -> None:
        entries = self.entries()
        entries.append(
            {"stage": stage, "run": run, "seconds": max(0.0, float(seconds)), "utc": datetime.now(UTC).isoformat()}
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        write_json(self.path, {"study": STUDY, "kind": "ledger", "cap_seconds": self.cap_seconds, "entries": entries})


def default_ledger(experiments_root: Path | None = None) -> Ledger:
    return Ledger((experiments_root or default_experiments_root()) / "P9I-ledger.json")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def labels_of(items: Iterable[Cell]) -> list[str]:
    return [c.label for c in items]


# --- which seed set a mode may touch ----------------------------------------------------------------------------
def check_seed_set(mode: str, seed_set_name: str) -> None:
    """``registered`` uses only the registered data seeds (182001 upward); ``calibration`` only rehearsal
    draw 1; ``rehearsal`` only the other rehearsal draws (0, 2..9); unit tests and the DRY stage use
    test seeds (900001 upward) in the calibration or rehearsal modes. Anything else is refused."""
    if mode not in ("registered", "calibration", "rehearsal"):
        raise ValueError(f"unknown mode {mode!r}")
    if mode == "registered":
        ok = seed_set_name == "p9i-registered"
    elif mode == "calibration":
        ok = seed_set_name == f"rehearsal-{CALIBRATION_DRAW}" or seed_set_name.startswith("p9i-test")
    else:
        draws = {f"rehearsal-{k}" for k in range(REHEARSAL_MAX_DRAW + 1) if k != CALIBRATION_DRAW}
        ok = seed_set_name in draws or seed_set_name.startswith("p9i-test")
    if not ok:
        raise ValueError(f"mode {mode!r} cannot use the {seed_set_name!r} seed set")


def make_cell(arm: str, slots: int, parent: tuple[int, int] = PRIMARY_PARENT, seed: int = INIT_SEEDS[0]) -> Cell:
    """A cell of any arm at any size without consulting the registry (unit tests and the DRY stage; a
    registered or calibration label is never made this way)."""
    block = "BB" if arm in BB_ARMS else "core"
    return Cell(block, "test", arm, slots, parent, seed, make_label(arm, slots, parent, seed, "TEST-"))
