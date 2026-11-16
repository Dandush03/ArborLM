# ruff: noqa: E501
"""P10S2 shared contract: the config, the oracle-assisted line, the seed registry (ADR-0022 section 9, gate G9) and record helpers.

Every generator in ``studies/p10s2`` is created by ``seeded_generator``, which refuses a seed outside the set allowed for the running mode, records the seed and its
purpose, and never derives one seed from another beyond the listed offsets (section 9: "no +1000*k derivation is used"). The global default generator is not used
(a source check in the tests enforces it).
"""

import math
import os
import tempfile
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


class TestGuardRefused(RuntimeError):
    """Registered or study-state code was asked to run under pytest against a directory that is not a temporary directory."""


# Directories a test may use as a run root: the temporary directory of the process and the usual system ones. The real repository (under the user's home) is never one of them; a throwaway clone made
# in a temporary directory (the end-to-end exercise) is.
_TEMP_ROOTS = ("/tmp", "/private/tmp", "/var/folders", "/private/var/folders", "/var/tmp", "/private/var/tmp")
REAL_ROOT = Path(__file__).resolve().parents[2]


def is_temporary(path: Path) -> bool:
    """True if ``path`` lies under a temporary directory."""
    p = Path(path).resolve()
    roots = [Path(tempfile.gettempdir()).resolve(), *(Path(r).resolve() for r in _TEMP_ROOTS)]
    return any(p.is_relative_to(r) for r in roots)


def is_test_configuration() -> bool:
    """True if every registered replicate base of the loaded configuration lies in the ADR's test namespace 229001-229999 (the end-to-end exercise's throwaway clone writes such a configuration; the real one never does)."""
    return all(229001 <= b <= 229999 for b in SEEDS["replicate_bases"])  # the ADR's test namespace


def refuse_under_pytest(*roots: Path, what: str = "a registered stage") -> None:
    """Under pytest (``PYTEST_CURRENT_TEST`` is set) registered code, the study ledger and the freeze files may only be used on a temporary directory: a test can never start a registered stage, write the real ledger or
    touch the real ``experiments/`` directory or the real repository."""
    if "PYTEST_CURRENT_TEST" not in os.environ:
        return
    for r in roots:
        p = Path(r).resolve()
        if p == REAL_ROOT or p.is_relative_to(REAL_ROOT):  # the checkout the code runs from (the repository, or an audit pin under /tmp): never a test's run root, whatever its location
            raise TestGuardRefused(f"refused under pytest: {what} was pointed at {r}, which is inside the checkout the code runs from ({REAL_ROOT})")
        if not is_temporary(r):
            raise TestGuardRefused(f"refused under pytest: {what} was pointed at {r}, which is not a temporary directory")


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
MODES = ("registered-run", "registered-data", "registered-analysis", "calibration", "rehearsal", "test")
SEEDS = CFG["seeds"]
OFFSETS: tuple[int, ...] = tuple(SEEDS["offsets"])
OFFSET_NAMES = {0: "stage-1 store", 1: "training draw", 2: "batch order", 3: "router", 4: "permutation controls", 5: "gold draw", 6: "stage-2 appended rows", 7: "M-joint store", 8: "LoRA initialization", 9: "E-table initialization", 10: "oracle-code hash"}
PARTITION_SEED: int = SEEDS["partition"]
_STREAM_NAMES = ("q_split", "source_sample", "ablation_subsample", "gen_windows", "bootstrap", "seen_items", "timing_items", "tokenizer_record", "random_id_sequences", "c1_pairing", "equivalence_injection")
# 220902-220912 in this order, from the configuration (the end-to-end exercise's throwaway clone substitutes test-range seeds there; the real configuration lists the real ones and a test compares them)
PARTITION_STREAMS: dict[str, int] = dict(zip(_STREAM_NAMES, SEEDS["partition_streams"], strict=True))
# The listed use of each partition-side seed (section 9 and the rulings of the three implementation audits: 220912 is the equivalence injection vector's own seed; 220906 is drawn in the analysis stage only).
PARTITION_USES: dict[str, str] = {
    "partition": "assignment of identity groups, then Q, D_cal, D_con, E_A, E_B, E_C, E_open",
    "q_split": "the split of Q into Q_fit and Q_check, by identity group",
    "source_sample": "the sample of at most 60,000 no-gold sources per capability (A, then B)",
    "ablation_subsample": "the 300-item ablation subsample of E_A and E_B",
    "gen_windows": "the selection of the 100 ordinary general-language (GEN) windows (the 44 marker-like windows of the fixed grid are all taken)",
    "bootstrap": "the bootstrap resampling of every printed interval: drawn in the ANALYSIS STAGE ONLY, a fresh generator per printed interval, in the order of the registry (ruling of 2026-11-15)",
    "seen_items": "the 300 seen-item training items (one permutation of each capability's accepted pool, A then B)",
    "timing_items": "the 200 items per panel of the timing benchmark (E_A, then E_B)",
    "tokenizer_record": "the 100 fixed sentences of each teacher's tokenizer record (A, then B)",
    "random_id_sequences": "the 1,000 random id sequences of test (c)",
    "c1_pairing": "the pairing of the combined task C1",
    "equivalence_injection": "the fixed vector added at the output of block L in equivalence test (d)",
}
ANALYSIS_STREAMS = ("bootstrap",)  # drawn in the analysis stage only; never in the data-generation step
TEST_PARTITION_BASE = 229950  # test-mode stand-ins for 220901..220912 (the test range is 229001-229999)
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
    """The partition-side seeds by name ('partition' and the streams). ``registered-data`` holds the eleven drawn in the data-generation and partition steps (220901-220905 and 220907-220912);
    ``registered-analysis`` holds 220906 alone (the bootstrap, drawn in the analysis stage only); test mode uses stand-ins inside the test range for all twelve."""
    names = ["partition", *PARTITION_STREAMS]
    if mode == "registered-data":
        return {"partition": PARTITION_SEED, **{n: s for n, s in PARTITION_STREAMS.items() if n not in ANALYSIS_STREAMS}}
    if mode == "registered-analysis":
        return {n: PARTITION_STREAMS[n] for n in ANALYSIS_STREAMS}
    if mode == "test":
        return {n: TEST_PARTITION_BASE + 1 + i for i, n in enumerate(names)}
    raise ValueError(f"mode {mode!r} has no partition-side seeds")


def listed_partition_seeds() -> dict[str, int]:
    """All twelve listed partition-side seeds, 220901-220912 (gate G9's list), by name."""
    return {"partition": PARTITION_SEED, **PARTITION_STREAMS}


def allowed_seeds(mode: str) -> frozenset[int]:
    if mode in ("registered-data", "registered-analysis"):
        return frozenset(partition_seeds(mode).values())
    if mode == "test":
        return frozenset(range(SEEDS["test_low"], SEEDS["test_high"] + 1))
    if mode in ("registered-run", "calibration", "rehearsal"):
        return frozenset(b + o for b in replicate_bases(mode) for o in OFFSETS)
    raise ValueError(f"unknown mode {mode!r}")


def planned_seeds(mode: str, replicates: int | None = None) -> list[int]:
    """Every seed a stage of ``mode`` may draw, every replicate included (sorted, without repeats): for the run modes, base + offset 0..10 of all ``replicates`` bases (all of them if None); for
    ``registered-data`` the eleven data-step seeds; for ``registered-analysis`` 220906."""
    if mode in ("registered-data", "registered-analysis"):
        return sorted(partition_seeds(mode).values())
    if mode in ("registered-run", "calibration", "rehearsal", "test"):
        bases = replicate_bases(mode)
        n = len(bases) if replicates is None else replicates
        return sorted({b + o for b in bases[:n] for o in OFFSETS})
    raise ValueError(f"unknown mode {mode!r}")


@dataclass(frozen=True)
class SeedUse:
    seed: int
    purpose: str
    mode: str
    kind: str = "generator"  # "generator" (a fresh torch.Generator) or "code-hash" (the +10 oracle-code seed: it seeds no generator but is still a use of a listed seed)


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


def record_code_seed_use(seed: int, purpose: str, mode: str) -> None:
    """Record a use of the +10 oracle-code seed (the hash seeds no generator, so G9 would not otherwise see it). The same refusal applies as for a generator."""
    if mode not in MODES:
        raise ValueError(f"unknown seed mode {mode!r}")
    if seed not in allowed_seeds(mode):
        raise SeedRefused(f"seed {seed} ({purpose}) is not in the set allowed for mode {mode!r}")
    _RECORD.append(SeedUse(seed, purpose, mode, "code-hash"))


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
        """The oracle-code hash seed (+10): the hash takes this listed seed and the pair as inputs and seeds no generator. Each call is a recorded use (gate G9 reads it)."""
        record_code_seed_use(self.seed(10), OFFSET_NAMES[10], self.mode)
        return self.seed(10)

    def planned(self) -> list[int]:
        return [self.seed(o) for o in OFFSETS]


def partition_gen(mode: str, name: str, purpose: str | None = None) -> torch.Generator:
    seeds = partition_seeds(mode)
    if name not in seeds:
        raise SeedRefused(f"partition-side stream {name!r} is not drawn in mode {mode!r}")
    return seeded_generator(seeds[name], purpose or name, mode)


def bootstrap_generator(mode: str, interval: str) -> torch.Generator:
    """The listed seed 220906 for one printed interval: a fresh generator per interval, drawn in the analysis stage only (mode ``registered-analysis``, or ``test``). ``interval`` names it
    (call in the order of the registry)."""
    return partition_gen(mode, "bootstrap", f"bootstrap interval {interval}")


def seed_table() -> list[dict[str, Any]]:
    """The seed table of the data manifest: every listed seed with its use and the stage that draws it. Registered replicates: all four bases and all eleven offsets (the +10 code seed included).
    Partition-side seeds: 220901-220912, with 220906 marked as drawn in the analysis stage only."""
    rows: list[dict[str, Any]] = []
    for i, base in enumerate(SEEDS["replicate_bases"]):
        for o in OFFSETS:
            rows.append({"seed": base + o, "name": f"replicate {i} +{o}", "use": OFFSET_NAMES[o], "stage": "registered run", "draws_generator": o != 10})
    for name, seed in listed_partition_seeds().items():
        rows.append({"seed": seed, "name": name, "use": PARTITION_USES[name], "stage": "analysis (only)" if name in ANALYSIS_STREAMS else "data generation and partition", "draws_generator": True})
    return rows


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
    """Replicate base + 0..10 for the four bases and 220901..220912 (G9's 'listed registered seeds')."""
    return frozenset(allowed_seeds("registered-run") | frozenset(listed_partition_seeds().values()))


REGISTERED_MODES = ("registered-run", "registered-data", "registered-analysis")


def seed_gate(
    records: Sequence[SeedUse], planned: Iterable[int] = (), *, planned_mode: str = "registered-run", extra_foreign: Iterable[int] = (), stage_mode: str | None = None, allow_partial: bool = False,
) -> dict[str, Any]:  # fmt: skip
    """Gate G9 on the seeds planned for the registry and on the seeds actually recorded. A problem is listed, never silently dropped.

    Without ``stage_mode`` this is the earlier, weaker check (kept for callers that have no stage). With ``stage_mode`` (the mode of the stage that is gated: ``registered-run`` in a registered
    process, ``registered-data`` in the data-generation step, ``registered-analysis`` in the analysis stage, ...) it is the strict check of the audit's M4: every recorded use must carry exactly that
    mode (a "test" or "rehearsal" use inside a registered process is refused), the record must not be empty, ``planned`` (built with ``planned_seeds`` for every replicate of the stages run) must not
    be empty, and the set of recorded seeds must equal the planned set (``allow_partial`` relaxes this to "recorded is a subset of planned" for a stage that is known to draw only part of it)."""
    problems: list[str] = []
    lo_r, hi_r = RANGES["registered"]
    reg = listed_registered_seeds()
    partition_side = frozenset(listed_partition_seeds().values())
    other_ranges = [RANGES["calibration"], RANGES["rehearsal"], RANGES["test"]]
    foreign_extra = frozenset(extra_foreign)
    planned_list = list(planned)

    def check_registered(seed: int, where: str) -> None:
        if seed not in reg:
            problems.append(f"{where}: registered seed {seed} is not a listed registered seed")
        if not lo_r <= seed <= hi_r:
            problems.append(f"{where}: {seed} lies outside {lo_r}-{hi_r}")
        for lo, hi in other_ranges:
            if lo <= seed <= hi:
                problems.append(f"{where}: {seed} lies inside {lo}-{hi}")

    for s in planned_list:
        hit_p = foreign_seed_hit(s, foreign_extra)
        if hit_p is not None:
            problems.append(f"planned seed {s} lies in the range of {hit_p}")
        if planned_mode in REGISTERED_MODES:
            check_registered(s, "planned")
        else:
            lo, hi = RANGES[planned_mode]
            if not lo <= s <= hi:
                problems.append(f"planned: {planned_mode} seed {s} lies outside {lo}-{hi}")
    for use in records:
        hit = foreign_seed_hit(use.seed, foreign_extra)
        if hit is not None:
            problems.append(f"recorded seed {use.seed} ({use.purpose}) lies in the range of {hit}")
        if stage_mode is not None and use.mode != stage_mode:
            problems.append(f"recorded[{use.purpose}]: seed {use.seed} carries mode {use.mode!r}, not the stage's {stage_mode!r}")
        if use.mode == "registered-run":
            check_registered(use.seed, f"recorded[{use.purpose}]")
            if use.seed in partition_side:
                problems.append(f"recorded[{use.purpose}]: {use.seed} is a partition-side seed used in the registered run")
        elif use.mode in ("registered-data", "registered-analysis"):
            if use.seed not in allowed_seeds(use.mode):
                analysis_only = use.seed in (PARTITION_STREAMS[n] for n in ANALYSIS_STREAMS)
                problems.append(f"recorded[{use.purpose}]: {use.seed} in mode {use.mode!r} " + ("is drawn in the analysis stage only" if analysis_only else "is not one of the seeds of that stage"))
        elif use.mode in ("calibration", "rehearsal", "test"):
            lo, hi = RANGES[use.mode]
            if not lo <= use.seed <= hi:
                problems.append(f"recorded[{use.purpose}]: {use.mode} seed {use.seed} lies outside {lo}-{hi}")
        else:
            problems.append(f"recorded[{use.purpose}]: unknown mode {use.mode!r}")
    if stage_mode is not None:
        recorded_set = {u.seed for u in records}
        if not records:
            problems.append("the seed record is empty: a stage that drew nothing cannot pass G9")
        if not planned_list:
            problems.append("no planned seeds were given: the gate needs the planned set of every replicate of the stages run")
        else:
            planned_set = set(planned_list)
            extra = sorted(recorded_set - planned_set)
            if extra:
                problems.append(f"recorded seeds that are not planned: {extra}")
            missing = sorted(planned_set - recorded_set)
            if missing and not allow_partial:
                problems.append(f"planned seeds never recorded: {missing}")
    return {
        "ok": not problems, "problems": problems, "recorded": [{"seed": u.seed, "purpose": u.purpose, "mode": u.mode, "kind": u.kind} for u in records], "stage_mode": stage_mode,
    }  # fmt: skip


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
