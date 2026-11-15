# ruff: noqa: E501
"""P10S2 shared contract: the config, the oracle-assisted line, the seed registry (ADR-0022 section 9, gate G9) and record helpers.

Every generator in ``studies/p10s2`` is created by ``seeded_generator``, which refuses a seed outside the set allowed for the running mode, records the seed and its
purpose, and never derives one seed from another beyond the listed offsets (section 9: "no +1000*k derivation is used"). The global default generator is not used
(a source check in the tests enforces it).
"""

import math
import tomllib
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch

from arborlm.io import canonical_json, sha256

STUDY = "P10S2"
SPEC = "docs/decisions/ADR-0022-p10-s2-two-teacher-transfer.md"
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = Path("configs/p10s2_transfer.toml")
LAUNCH_DIR = Path("studies/p10s2/launch")
FREEZE_DIR = Path("studies/p10s2/freeze")
PLAN_FILE = FREEZE_DIR / "plan.json"
CAPS_FILE = FREEZE_DIR / "stage_caps.json"
RAISE_FILE = FREEZE_DIR / "cap_raise.json"
SCHEMA = 1

# The fixed line of section 11.3. Every class, mechanism, router, composition and cost line, table, caption, machine-readable record and log summary is headed by it.
ORACLE_LINE = (
    "oracle-assisted (word-level addresses supplied by rule); lexical translation of short closed-vocabulary sentences, two capabilities of one kind; "
    "frozen English student; teacher-only training material verified by measured-precision filter; not autonomous learned memory."
)
# The second fixed line of the combined-tasks addendum section 9, on every composition line and every composition table.
COMBINED_LINE = "combined tasks: the routes, the order of the answers and the summing of reads are supplied by rule; neither combined task was trained on; descriptive; enters no gate, class or label."
COMPOSITION_WORDS = ("COMPOSES", "DOES NOT COMPOSE", "COMPOSITION INCONCLUSIVE")
LEAD_RULE = "S1 and S2 must not claim autonomous learned-memory success from oracle-assisted results."
# Words that carry a class, mechanism, router, composition or cost reading (section 11.3, "No positive wording without it"). Matched as substrings.
GUARDED_WORDS = (
    "ACQUIRES-AND-RETAINS", "TRANSFER-POSITIVE", "QUALIFIED", "COMPOSES", "TRAINING COST COMPARABLE", "FEWER VALUE ROWS ACTIVE", "TRANSFER-NEGATIVE",
    "TRANSFER-INCONCLUSIVE", "NO-NEW-CAPABILITY", "FORGETS", "RETENTION BY INERTIA", "NOT REPLICATED", "INTERMEDIATE", "NOT_EVALUATED", "ENGINEERING-FAILURE",
    "INCOMPLETE", "BY CONSTRUCTION", "TRAINING COST HIGHER", "NO ADVANTAGE OVER SEPARATE ADAPTERS", "EQUIVALENT TO A WORD TABLE", "RETRIEVAL SUFFICES",
    "LEXICON-EQUIVALENT", "TEACHER-EQUIVALENT-TO-GOLD", "BELOW JOINT BOUND", "BELOW ADAPTER JOINT", "TASK-CODED SPARSE RETENTION", "APPEND COST",
    "EXACT-MATCH WEAK", "DOES NOT COMPOSE", "COMPOSITION INCONCLUSIVE", "composition (replaced)", "ROUTER (keyword-level)", "CONSOLIDATION-REJECTED", "NOT STARTED", "NO PERMUTATION CONTROL (ADAPTER)",
)  # fmt: skip


class PendingLeadReview(RuntimeError):
    """An item the ADR leaves open or cannot support; the code stops there instead of choosing a scientific value."""


def load_config(path: Path | None = None) -> dict[str, Any]:
    p = path if path is not None else ROOT / DEFAULT_CONFIG
    with p.open("rb") as f:
        return tomllib.load(f)


CFG: dict[str, Any] = load_config()
CONFIG_SHA256 = sha256((ROOT / DEFAULT_CONFIG).read_bytes())

KEY_WIDTH: int = CFG["memory"]["key_width"]
TOP: int = CFG["memory"]["top"]
TEMPERATURE: float = CFG["memory"]["temperature"]
ROWS_PER_STAGE: int = CFG["memory"]["rows_per_stage"]
INIT_STD: float = CFG["memory"]["init_std"]
READ_LAYERS: tuple[int, ...] = tuple(CFG["memory"]["read_layers"])
BATCH: int = CFG["training"]["batch"]
VOCABULARY: int = CFG["data"]["vocabulary"]
MARKER_INDEX: int = VOCABULARY  # j = 2,000 is the task marker (section 5.4)
TASKS = ("A", "B")  # A: English -> German, B: English -> French
TASK_NUMBER = {"A": 0, "B": 1}
ORDERS = ("AB", "BA")  # the first capability then the second
GAP_MIN: float = CFG["scoring"]["gap_denominator_min"]
NOT_EVALUATED = "NOT_EVALUATED"


def other_task(task: str) -> str:
    return "B" if task == "A" else "A"


# --- seeds (section 9, gate G9) --------------------------------------------------------------------------------------------------------------
MODES = ("registered-run", "registered-data", "calibration", "rehearsal", "test")
SEEDS = CFG["seeds"]
OFFSETS: tuple[int, ...] = tuple(SEEDS["offsets"])
OFFSET_NAMES = {0: "stage-1 store", 1: "training draw", 2: "batch order", 3: "router", 4: "permutation controls", 5: "gold draw", 6: "stage-2 appended rows", 7: "M-joint store", 8: "LoRA initialization", 9: "E-table initialization", 10: "oracle-code hash"}
PARTITION_SEED: int = SEEDS["partition"]
PARTITION_STREAMS: dict[str, int] = {"q_split": 220902, "source_sample": 220903, "ablation_subsample": 220904, "gen_windows": 220905, "bootstrap": 220906, "seen_items": 220907, "timing_items": 220908, "tokenizer_record": 220909, "random_id_sequences": 220910, "c1_pairing": 220911}
TEST_PARTITION_BASE = 229950  # test-mode stand-ins for 220901..220910 (the test range is 229001-229999)
RANGES = {
    "registered": (SEEDS["registered_low"], SEEDS["registered_high"]),
    "calibration": (SEEDS["calibration_low"], SEEDS["calibration_high"]),
    "rehearsal": (SEEDS["rehearsal_low"], SEEDS["rehearsal_high"]),
    "test": (SEEDS["test_low"], SEEDS["test_high"]),
}


def replicate_bases(mode: str) -> tuple[int, ...]:
    if mode == "registered-run":
        return tuple(SEEDS["replicate_bases"])
    if mode == "calibration":
        return tuple(SEEDS["calibration_base"] + SEEDS["draw_stride"] * i for i in range(SEEDS["draw_count"]))
    if mode == "rehearsal":
        return tuple(SEEDS["rehearsal_base"] + SEEDS["draw_stride"] * i for i in range(SEEDS["draw_count"]))
    if mode == "test":
        return tuple(SEEDS["test_low"] + SEEDS["draw_stride"] * i for i in range(4))  # 229001, 229101, 229201, 229301
    raise ValueError(f"mode {mode!r} has no replicate bases")


def partition_seeds(mode: str) -> dict[str, int]:
    """The ten partition-side seeds 220901..220910 by name ('partition' and the nine streams); test mode uses stand-ins inside the test range."""
    names = ["partition", *PARTITION_STREAMS]
    if mode == "registered-data":
        return {"partition": PARTITION_SEED, **PARTITION_STREAMS}
    if mode == "test":
        return {n: TEST_PARTITION_BASE + 1 + i for i, n in enumerate(names)}
    raise ValueError(f"mode {mode!r} has no partition-side seeds")


def allowed_seeds(mode: str) -> frozenset[int]:
    if mode == "registered-data":
        return frozenset(partition_seeds(mode).values())
    if mode == "test":
        return frozenset(range(SEEDS["test_low"], SEEDS["test_high"] + 1))
    if mode in ("registered-run", "calibration", "rehearsal"):
        return frozenset(b + o for b in replicate_bases(mode) for o in OFFSETS)
    raise ValueError(f"unknown mode {mode!r}")


@dataclass(frozen=True)
class SeedUse:
    seed: int
    purpose: str
    mode: str


_RECORD: list[SeedUse] = []


def reset_seed_record() -> None:
    _RECORD.clear()


def seed_record() -> list[SeedUse]:
    return list(_RECORD)


class SeedRefused(ValueError):
    """A seed outside the set allowed for the running stage (G9)."""


def seeded_generator(seed: int, purpose: str, mode: str) -> torch.Generator:
    """The only way a generator is made in this package: a fresh ``torch.Generator`` seeded directly with ``seed``, which must be in the set ``mode`` allows. The use is recorded
    (gate G9 reads the record). A seed outside its set stops the run."""
    if mode not in MODES:
        raise ValueError(f"unknown seed mode {mode!r}")
    if seed not in allowed_seeds(mode):
        raise SeedRefused(f"seed {seed} ({purpose}) is not in the set allowed for mode {mode!r}")
    _RECORD.append(SeedUse(seed, purpose, mode))
    return torch.Generator().manual_seed(seed)


@dataclass(frozen=True)
class SeedPlan:
    """The seeds of one replicate: base + offset 0..10 (section 9). ``mode`` is registered-run, calibration, rehearsal or test; ``index`` the replicate (0..3 registered)."""

    mode: str
    index: int

    @property
    def base(self) -> int:
        return replicate_bases(self.mode)[self.index]

    def seed(self, offset: int) -> int:
        if offset not in OFFSETS:
            raise ValueError(f"offset {offset} is not listed")
        return self.base + offset

    def gen(self, offset: int, purpose: str | None = None) -> torch.Generator:
        """A fresh generator for one use of the seed (section 9: every use of a listed seed starts a fresh generator)."""
        return seeded_generator(self.seed(offset), purpose or OFFSET_NAMES[offset], self.mode)

    def code_seed(self) -> int:
        """The oracle-code hash seed (+10): the hash takes this listed seed and the pair as inputs and seeds no generator."""
        return self.seed(10)

    def planned(self) -> list[int]:
        return [self.seed(o) for o in OFFSETS]


def partition_gen(mode: str, name: str, purpose: str | None = None) -> torch.Generator:
    seeds = partition_seeds(mode)
    return seeded_generator(seeds[name], purpose or name, mode)


# --- namespaces S2 must stay disjoint from (section 9) -----------------------------------------------------------------------------------------
def foreign_ranges() -> dict[str, tuple[tuple[int, int], ...]]:
    """P1-P9-II as listed in ADR-0021 section 6.3, S0 and S1 as listed in ADR-0022 section 9. The seeds of P1-P8 are read from their configs by ``config_seeds``."""
    return {
        "P9": ((170001, 171343), (179001, 179933), (1701, 1702)),
        "P9-I": ((182001, 182020), (180101, 181900), (1791, 1792), (1801, 1802), (900001, 900233)),
        "review": ((500001, 500004), (941001, 941001)),
        "P9-II": ((190001, 191599), (1891, 1892), (1901, 1902), (910001, 919999)),
        "S0": ((200001, 209999), (2001, 2002), (2091, 2092), (920001, 920999)),
        "S1": ((210001, 219999), (2101, 2105), (2111, 2112), (2121, 2122), (2191, 2192), (921001, 921999)),
    }


def foreign_seed_hit(seed: int, extra: Iterable[int] = ()) -> str | None:
    for name, spans in foreign_ranges().items():
        if any(lo <= seed <= hi for lo, hi in spans):
            return name
    return "P1-P8 configs" if seed in set(extra) else None


def config_seeds(config_dir: Path | None = None) -> frozenset[int]:
    """Every integer stored under a key containing 'seed' in the committed configs of the other studies (read-only), for the disjointness check of gate G9."""
    found: set[int] = set()

    def walk(obj: Any, key: str = "") -> None:
        if isinstance(obj, Mapping):
            for k, v in obj.items():
                walk(v, str(k))
        elif isinstance(obj, Sequence) and not isinstance(obj, str):
            for v in obj:
                walk(v, key)
        elif isinstance(obj, int) and not isinstance(obj, bool) and "seed" in key.lower():
            found.add(obj)

    d = config_dir if config_dir is not None else ROOT / "configs"
    for p in sorted(d.glob("*.toml")):
        if p.name == DEFAULT_CONFIG.name:
            continue
        with p.open("rb") as f:
            walk(tomllib.load(f))
    return frozenset(found)


def listed_registered_seeds() -> frozenset[int]:
    """Replicate base + 0..10 for the four bases and 220901..220910 (G9's 'listed registered seeds')."""
    return frozenset(allowed_seeds("registered-run") | allowed_seeds("registered-data"))


def seed_gate(records: Sequence[SeedUse], planned: Iterable[int] = (), *, planned_mode: str = "registered-run", extra_foreign: Iterable[int] = ()) -> dict[str, Any]:
    """Gate G9 on the seeds planned for the registry and on the seeds actually recorded. A problem is listed, never silently dropped."""
    problems: list[str] = []
    lo_r, hi_r = RANGES["registered"]
    reg = listed_registered_seeds()
    other_ranges = [RANGES["calibration"], RANGES["rehearsal"], RANGES["test"]]
    foreign_extra = frozenset(extra_foreign)

    def check_registered(seed: int, where: str) -> None:
        if seed not in reg:
            problems.append(f"{where}: registered seed {seed} is not a listed registered seed")
        if not lo_r <= seed <= hi_r:
            problems.append(f"{where}: {seed} lies outside {lo_r}-{hi_r}")
        for lo, hi in other_ranges:
            if lo <= seed <= hi:
                problems.append(f"{where}: {seed} lies inside {lo}-{hi}")

    for s in planned:
        hit_p = foreign_seed_hit(s, foreign_extra)
        if hit_p is not None:
            problems.append(f"planned seed {s} lies in the range of {hit_p}")
        if planned_mode in ("registered-run", "registered-data"):
            check_registered(s, "planned")
        else:
            lo, hi = RANGES[planned_mode]
            if not lo <= s <= hi:
                problems.append(f"planned: {planned_mode} seed {s} lies outside {lo}-{hi}")
    for use in records:
        hit = foreign_seed_hit(use.seed, foreign_extra)
        if hit is not None:
            problems.append(f"recorded seed {use.seed} ({use.purpose}) lies in the range of {hit}")
        if use.mode == "registered-run":
            check_registered(use.seed, f"recorded[{use.purpose}]")
            if use.seed in allowed_seeds("registered-data"):
                problems.append(f"recorded[{use.purpose}]: {use.seed} is a partition-side seed used in the registered run")
        elif use.mode == "registered-data":
            if use.seed not in allowed_seeds("registered-data"):
                problems.append(f"recorded[{use.purpose}]: {use.seed} is not one of 220901-220910")
        elif use.mode in ("calibration", "rehearsal", "test"):
            lo, hi = RANGES[use.mode]
            if not lo <= use.seed <= hi:
                problems.append(f"recorded[{use.purpose}]: {use.mode} seed {use.seed} lies outside {lo}-{hi}")
        else:
            problems.append(f"recorded[{use.purpose}]: unknown mode {use.mode!r}")
    return {"ok": not problems, "problems": problems, "recorded": [{"seed": u.seed, "purpose": u.purpose, "mode": u.mode} for u in records]}


# --- hashing and records ---------------------------------------------------------------------------------------------------------------------
def jsonable(x: Any) -> Any:
    """Non-finite floats are written as strings so a record survives JSON."""
    if isinstance(x, float):
        return x if math.isfinite(x) else ("nan" if math.isnan(x) else ("inf" if x > 0 else "-inf"))
    if isinstance(x, Mapping):
        return {str(k): jsonable(v) for k, v in x.items()}
    if isinstance(x, list | tuple):
        return [jsonable(v) for v in x]
    return x


def number(x: Any) -> float:
    """Inverse of ``jsonable`` for one number."""
    return float(x)


def digest(obj: Any) -> str:
    return sha256(canonical_json(jsonable(obj)))


def finite(x: float) -> bool:
    return math.isfinite(x)
