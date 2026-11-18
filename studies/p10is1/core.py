# ruff: noqa: E501
"""P10IS1 shared contract (ADR-0024 block M): the config (every threshold is read from ``configs/p10is1_capacity.toml`` and nowhere else), the grid, the arms, the rate units, the ladder and the snapshot
schedules, the cell specifications, the seeds, the DEP-c quantile, the read key scheme, the record kinds and record IO, and the charged-time ledger.

Torch is imported only through the functions that name a P10-S1 object (``chance_high``, ``bits``, ``floor_i_bits``, ``make_cell_spec``, the seed sets); the label and analysis modules call those lazily.
The ADR text is not a frozen input: ``spec_sha256`` is for provenance only.
"""

import functools
import math
import re
import tomllib
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from arborlm.io import file_sha256, read_json, write_json

STUDY = "P10IS1"
FAMILY = "P10IS1_CAPACITY_SCALING"
SCHEMA = 1
SPEC = "docs/decisions/ADR-0024-p10-i-s1-capacity-scaling.md"
CONFIG = Path("configs/p10is1_capacity.toml")
FREEZE_DIR = Path("studies/p10is1/freeze")
PLAN = FREEZE_DIR / "plan.json"
LAUNCH_DIR = Path("studies/p10is1/launch")

STANDING_TAG = "STORE ONLY; ORACLE-ADDRESSED; RECALL OF TRAINED RANDOM FACTS; DICT DOMINATES ON THIS TASK"
NOT_TESTED_X = "16,384→65,536 NOT TESTED — BLOCK X NOT APPROVED"
SIZES_CAPACITY = "1,024 TO 16,384 SLOTS"
LANE_L_NOT_LICENSED = "LANE L: OMITTED — NOT LICENSED"
LANE_L_NOT_LICENSED_AT_FREEZE = "LANE L: OMITTED — NOT LICENSED AT THE FREEZE"
LANE_L_LICENSED = "LANE L LICENSED — NOT YET SPECIFIED; NOT RUN UNDER THIS APPROVAL"

MODES = ("registered", "rehearsal", "test")
REGISTERED, REHEARSAL, TEST = MODES

ARMS = ("F-OQ", "T-OQ", "H8", "D-OQ", "R2")
STORE_ARMS = ("F-OQ", "T-OQ", "H8")  # the arms whose fullness the saturation rule reads (ruling 27)
CLASSIFIED_ARMS = ("F-OQ", "F-OQ-IVF", "T-OQ", "H8")
DECISION_ARMS = ("F-OQ", "F-OQ-IVF", "T-OQ")  # arms of C-CAPACITY rows 3 to 5
TRAINED_ENTRY_ARMS = ("F-OQ", "T-OQ")  # the only arms that may carry a label another study uses for entry
EFFICIENCY_ARMS = ("F-OQ", "T-OQ")
PANELS = ("A", "B")
READS = ("main", "ivf")
RECORD_KINDS = (
    "eval", "baseline", "train", "snapshot", "gate", "stage_manifest", "freeze_plan", "freeze_record", "analysis", "ledger", "rehearsal", "calibration", "calibration_run", "timing", "throughput", "decision",
    "identity_gate", "gates_record", "report_manifest", "engineering_stop", "projection", "quiet_attempt", "memory_check", "task_done",
)  # fmt: skip


# --- the config ----------------------------------------------------------------------------------------------------------------------
def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


_REQUIRED: dict[str, tuple[str, ...]] = {
    "thresholds": (
        "ref_r2_min", "dep_use_floor", "dep_c_tail", "dep_c_floor", "gain_min", "null_max", "plateau_max", "plateau_floor_a_use", "plateau_floor_i_printed", "loaded_i_max", "ceiling_i", "a_use_floor_capacity",
        "arm_a_use_at_largest", "dense_ahead_bits", "beats_dense_ratio", "tree_ahead_ratio", "tree_competitive_ratio", "saturation_ratio", "efficiency_i_t", "efficiency_updates_factor", "efficiency_cost_factor",
        "dense_faster_cost", "calibration_a_use_foq", "calibration_a_use_r2", "undertrained_a_use", "paired_all", "paired_most", "replicates", "sparse_ratio_min_replicates", "not_evaluated_min", "panel_disagree_min",
        "not_full_min", "unloaded_min",
    ),
    "mc": ("grid",),
    "rates": ("grid", "tie_difference", "extension_up", "extension_down", "extensions_max", "provisional_readout", "loaded_readout", "walk_steps"),
    "ladder": ("base", "factors_half_units", "half_unit", "levels", "u_p_candidates", "u_p_ceiling", "doubling_from", "u_p_multiples", "snapshot_fractions", "run_multiplier", "r2_run_multiplier", "calibration_ceiling", "p10s1_run", "calibration_i_max"),
    "grid": ("cells", "saturation_only_cell", "loaded_cells", "saturation_cells", "doq_cells", "r2_cells", "h8_cells", "row_facts", "u_p_larger_step_cell", "r2_reference_cell", "table_facts", "trained_configurations", "registered_cells", "registered_cells_without_256", "steps"),
    "seeds": ("registered_base", "registered_stride", "registered_draws", "init_base", "calibration_bases", "calibration_init", "rehearsal_base", "rehearsal_init", "test_base", "test_top", "test_init", "h8_offset", "index_offset", "identity_gate_draw", "identity_gate_init", "identity_gate_updates", "identity_gate_cell"),
    "seed_ranges": ("registered", "calibration", "rehearsal", "init", "test", "checker", "checker_sha256", "checker_allocation_name"),
    "platform": ("system", "machine", "torch", "torch_num_threads", "torch_interop_threads", "deterministic_algorithms"),
    "resources": ("workers", "workers_alternatives", "rss_worker_bytes", "rss_aggregate_bytes", "eval_chunk_elements"),
    "quiet": ("load_average_max", "poll_seconds", "session_hours", "attempts", "not_measured_after_paused_attempts", "timing_warmup_updates", "timing_updates", "timing_repeats", "throughput_batches", "throughput_repeats", "throughput_cv_max"),
    "memory_check": ("retry_seconds", "max_hours", "page_kinds"),
    "budget": ("total_cap_hours", "level_count", "cell_order", "cap_rule"),
    "caps": ("provisional", "rehearsal_hours", "calibration_hours", "train_hours", "evaluate_hours", "timing_hours", "throughput_hours", "analysis_hours", "total_hours"),
    "rehearsal": ("synthetic_facts", "synthetic_table", "synthetic_unseen", "synthetic_slots", "synthetic_updates"),
}  # fmt: skip


def validate_config(data: Mapping[str, Any]) -> Mapping[str, Any]:
    """Every section and key must exist and every number must be finite. Values are not compared with constants here: the config is the one place they live (a test compares them with the ADR)."""
    if data.get("schema_version") != SCHEMA or data.get("experiment_family") != FAMILY or data.get("spec_reference") != SPEC:
        raise ValueError("P10IS1 config: schema_version, experiment_family or spec_reference differ")
    for section, keys in _REQUIRED.items():
        block = data.get(section)
        if not isinstance(block, dict):
            raise ValueError(f"P10IS1 config: section [{section}] is missing")
        missing = [k for k in keys if k not in block]
        if missing:
            raise ValueError(f"P10IS1 config: [{section}] lacks {missing}")

    def walk(v: Any) -> None:
        if isinstance(v, float) and not math.isfinite(v):
            raise ValueError("P10IS1 config: a non-finite number")
        if isinstance(v, dict):
            for x in v.values():
                walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)

    walk(data)
    return data


def load_config(path: Path | None = None) -> Mapping[str, Any]:
    with (path or repo_root() / CONFIG).open("rb") as stream:
        return validate_config(tomllib.load(stream))


def config_sha256(path: Path | None = None) -> str:
    return file_sha256(path or repo_root() / CONFIG)


def spec_sha256(root: Path | None = None) -> str:
    """Provenance only: the ADR text is not in the frozen-input set (section 18)."""
    return file_sha256((root or repo_root()) / SPEC)


@functools.cache
def _cached_config() -> Mapping[str, Any]:
    return load_config()


def cfg_of(cfg: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return cfg if cfg is not None else _cached_config()


@dataclass(frozen=True)
class Thresholds:
    """Every scientific threshold of the labels, from the config (section 15 'Scientific threshold')."""

    ref_r2_min: float
    dep_use_floor: float
    dep_c_tail: float
    dep_c_floor: float
    gain_min: float
    null_max: float
    plateau_max: float
    plateau_floor_i: float
    loaded_i_max: float
    ceiling_i: float
    a_use_floor_capacity: float
    arm_a_use_at_largest: float
    dense_ahead_bits: float
    beats_dense_ratio: float
    tree_ahead_ratio: float
    tree_competitive_ratio: float
    saturation_ratio: float
    efficiency_i_t: float
    efficiency_updates_factor: float
    efficiency_cost_factor: float
    dense_faster_cost: float
    paired_all: int
    paired_most: int
    replicates: int
    not_evaluated_min: int
    panel_disagree_min: int
    not_full_min: int
    unloaded_min: int
    mc_grid: tuple[float, ...]

    @classmethod
    def from_config(cls, cfg: Mapping[str, Any] | None = None) -> "Thresholds":
        c = cfg_of(cfg)
        t = c["thresholds"]
        return cls(
            float(t["ref_r2_min"]), float(t["dep_use_floor"]), float(t["dep_c_tail"]), float(t["dep_c_floor"]), float(t["gain_min"]), float(t["null_max"]), float(t["plateau_max"]), floor_i_bits(float(t["plateau_floor_a_use"])),
            float(t["loaded_i_max"]), float(t["ceiling_i"]), float(t["a_use_floor_capacity"]), float(t["arm_a_use_at_largest"]), float(t["dense_ahead_bits"]), float(t["beats_dense_ratio"]), float(t["tree_ahead_ratio"]),
            float(t["tree_competitive_ratio"]), float(t["saturation_ratio"]), float(t["efficiency_i_t"]), float(t["efficiency_updates_factor"]), float(t["efficiency_cost_factor"]), float(t["dense_faster_cost"]),
            int(t["paired_all"]), int(t["paired_most"]), int(t["replicates"]), int(t["not_evaluated_min"]), int(t["panel_disagree_min"]), int(t["not_full_min"]), int(t["unloaded_min"]), tuple(float(x) for x in c["mc"]["grid"]),
        )  # fmt: skip


# --- information of a count (P10-S1's own functions, imported on call) --------------------------------------------------------------------
def floor_i_bits(a_use: float) -> float:
    """i at ``a_use`` by P10-S1's function (``studies.p9.core.fano_bits_per_fact``): 0.473 bits at a_use 0.25."""
    from studies.p9 import core as p9core

    return float(p9core.fano_bits_per_fact(a_use))


@functools.cache
def chance_high(n: int) -> int:
    """The upper end of the G2 chance interval for ``n`` facts (P10-S1's ``chance_interval``)."""
    from studies.p10s1 import core as s1

    return int(s1.chance_interval(n).high)


@functools.cache
def chance_low(n: int) -> int:
    from studies.p10s1 import core as s1

    return int(s1.chance_interval(n).low)


def at_chance(correct: int, n: int) -> bool:
    """Inside the G2 interval (an empty set is at chance)."""
    if n <= 0:
        return True
    return chance_low(n) <= correct <= chance_high(n)


def bits(useful: int, n: int) -> float:
    """i in bits per fact (P10-S1's ``bits_per_fact``: zero at or below the upper end of the chance interval)."""
    from studies.p10s1 import core as s1

    return float(s1.bits_per_fact(useful, n))


# --- DEP-c (section 8.1) --------------------------------------------------------------------------------------------------------------
def _log_add(a: float, b: float) -> float:
    if a == -math.inf:
        return b
    if b == -math.inf:
        return a
    hi, lo = (a, b) if a >= b else (b, a)
    return hi + math.log1p(math.exp(lo - hi))


def binomial_upper_quantile(m: int, p: float, tail: float) -> int:
    """The smallest k with P(X <= k) >= 1 - tail for X ~ Binomial(m, p), computed exactly in log space (no package outside the lock; ruling 20). 'Exceeds' in DEP-c means strictly greater than this k."""
    if m < 0 or not 0.0 <= p <= 1.0 or not 0.0 < tail < 1.0:
        raise ValueError("binomial_upper_quantile: m >= 0, 0 <= p <= 1, 0 < tail < 1")
    if m == 0 or p == 0.0:
        return 0
    if p == 1.0:
        return m
    target = math.log1p(-tail)
    lp = m * math.log1p(-p)  # log P(X = 0)
    cum = lp
    k = 0
    ratio = math.log(p) - math.log1p(-p)
    while cum < target and k < m:
        lp += math.log(m - k) - math.log(k + 1) + ratio
        k += 1
        cum = _log_add(cum, lp)
    return k


@functools.lru_cache(maxsize=4096)
def dep_c_quantile(n: int, u: int, tail: float) -> int:
    """Part (i) of DEP-c: the upper 1 - tail quantile of Binomial(m, p+) with m = n - u facts not usefully retained and p+ the upper end of the G2 chance interval for n divided by n."""
    return binomial_upper_quantile(n - u, chance_high(n) / n, tail)


def dep_c_fails(n: int, correct: int, useful: int, baseline_correct: int, *, tail: float, floor: float) -> bool:
    """DEP-c fails only if BOTH (i) c - u exceeds the upper 1 - tail quantile of Binomial(m, p+) and (ii) (c - u - m b/n) / n > floor (section 8.1). n facts, c correct answers, u useful, m = n - u, b the no-memory
    baseline's correct count on the same panel and fact set."""
    if n <= 0:
        return False
    m = n - useful
    excess = correct - useful
    part_i = excess > dep_c_quantile(n, useful, tail)
    part_ii = (excess - m * baseline_correct / n) / n > floor
    return bool(part_i and part_ii)


# --- names, steps, units ------------------------------------------------------------------------------------------------------------
def size_name(n: int) -> str:
    return f"{n // 1024}K" if n % 1024 == 0 else str(n)


def cell_name(facts: int, slots: int) -> str:
    """``8K/4K``: 8,192 facts in 4,096 slots."""
    return f"{size_name(facts)}/{size_name(slots)}"


def cell_key(facts: int, slots: int) -> str:
    """``8192/4096``: the machine key of a cell (config keys)."""
    return f"{facts}/{slots}"


def pairs(values: Iterable[Sequence[int]]) -> tuple[tuple[int, int], ...]:
    return tuple((int(v[0]), int(v[1])) for v in values)


def grid_cells(cfg: Mapping[str, Any] | None = None) -> tuple[tuple[int, int], ...]:
    return pairs(cfg_of(cfg)["grid"]["cells"])


def loaded_cells(cfg: Mapping[str, Any] | None = None) -> tuple[tuple[int, int], ...]:
    return pairs(cfg_of(cfg)["grid"]["loaded_cells"])


def saturation_only_cell(cfg: Mapping[str, Any] | None = None) -> tuple[int, int]:
    v = cfg_of(cfg)["grid"]["saturation_only_cell"]
    return int(v[0]), int(v[1])


def ladder_cells(cfg: Mapping[str, Any] | None = None, *, sat256: bool = True) -> tuple[tuple[int, int], ...]:
    """The cells that run until full within a budget, in the fixed order of section 17.1 (ascending load, then ascending facts): 2K/256 (when it runs), 8K/1K, 32K/4K."""
    order = pairs(cfg_of(cfg)["budget"]["cell_order"])
    return tuple(c for c in order if sat256 or c != saturation_only_cell(cfg))


def is_ladder_cell(facts: int, slots: int, cfg: Mapping[str, Any] | None = None) -> bool:
    return (facts, slots) in pairs(cfg_of(cfg)["budget"]["cell_order"])


def doq_cells(cfg: Mapping[str, Any] | None = None) -> tuple[tuple[int, int], ...]:
    return pairs(cfg_of(cfg)["grid"]["doq_cells"])


def r2_cells(cfg: Mapping[str, Any] | None = None) -> tuple[tuple[int, int], ...]:
    return pairs(cfg_of(cfg)["grid"]["r2_cells"])


def row_facts(cfg: Mapping[str, Any] | None = None) -> tuple[int, ...]:
    return tuple(int(x) for x in cfg_of(cfg)["grid"]["row_facts"])


def arm_cells(arm: str, cfg: Mapping[str, Any] | None = None, *, sat256: bool = True) -> tuple[tuple[int, int], ...]:
    """Cells of ``arm`` (section 5): F-OQ at the seven and 2K/256 (unless the calibration fixed it as not run), T-OQ and H8 at the seven, D-OQ at the six, R2 at its three."""
    c = cfg_of(cfg)
    if arm == "F-OQ":
        return (*grid_cells(c), saturation_only_cell(c)) if sat256 else grid_cells(c)
    if arm in ("T-OQ", "H8"):
        return grid_cells(c)
    if arm == "D-OQ":
        return doq_cells(c)
    if arm == "R2":
        return r2_cells(c)
    raise ValueError(f"no cells for arm {arm!r}")


@dataclass(frozen=True)
class Step:
    name: str
    facts: int
    small: int
    large: int
    kind: str

    @property
    def transition(self) -> str:
        return f"{size_name(self.small)}→{size_name(self.large)}"

    @property
    def cells(self) -> tuple[tuple[int, int], tuple[int, int]]:
        return (self.facts, self.small), (self.facts, self.large)


def steps(cfg: Mapping[str, Any] | None = None) -> tuple[Step, ...]:
    return tuple(Step(str(s[0]), int(s[1]), int(s[2]), int(s[3]), str(s[4])) for s in cfg_of(cfg)["grid"]["steps"])


def step_by_name(name: str, cfg: Mapping[str, Any] | None = None) -> Step:
    for s in steps(cfg):
        if s.name == name:
            return s
    raise ValueError(f"no step {name!r}")


TRANSITIONS = ("1K→4K", "4K→16K")


def transitions(cfg: Mapping[str, Any] | None = None) -> dict[str, list[str]]:
    """Transition name -> the steps that make it (C1 and N1: 1K→4K; C2 and N2: 4K→16K)."""
    out: dict[str, list[str]] = {t: [] for t in TRANSITIONS}
    for s in steps(cfg):
        out[s.transition].append(s.name)
    return out


def saturation_pairs(cfg: Mapping[str, Any] | None = None) -> dict[str, tuple[tuple[int, int], ...]]:
    """Registered saturation pairs (slots N, 4N): 256→1,024 (F-OQ), 1,024→4,096 (F-OQ, F-OQ-IVF, T-OQ, H8) (section 9.4)."""
    return {"F-OQ": ((256, 1024), (1024, 4096)), "F-OQ-IVF": ((1024, 4096),), "T-OQ": ((1024, 4096),), "H8": ((1024, 4096),)}


def saturation_cell_of_slots(slots: int, cfg: Mapping[str, Any] | None = None) -> tuple[int, int]:
    """The cell of eight facts per slot at ``slots`` slots: 2K/256, 8K/1K, 32K/4K."""
    for f, n in pairs(cfg_of(cfg)["grid"]["saturation_cells"]):
        if n == slots:
            return f, n
    raise ValueError(f"no saturation cell with {slots} slots")


def trained_configurations(cfg: Mapping[str, Any] | None = None, *, sat256: bool = True) -> int:
    return sum(len(arm_cells(a, cfg, sat256=sat256)) for a in ARMS)


# rate units (section 7.1) -----------------------------------------------------------------------------------------------------------
def unit_key(arm: str, facts: int, slots: int, cfg: Mapping[str, Any] | None = None) -> str:
    """The rate unit of an arm at a cell. F-OQ, T-OQ, H8: 1,024 slots -> 2K/1K; 4,096 -> 8K/4K; 16,384 -> 32K/16K; the loaded cells and 2K/256 are their own units. D-OQ: 4,096 and 16,384 shared, the loaded cells
    their own. R2: one unit per reference cell. Keys: ``F-OQ|1024``, ``F-OQ|8K/1K``, ``D-OQ|4096``, ``R2|2K/4K``."""
    c = cfg_of(cfg)
    if arm == "R2":
        return f"R2|{cell_name(facts, slots)}"
    if is_ladder_cell(facts, slots, c):
        return f"{arm}|{cell_name(facts, slots)}"
    if arm == "D-OQ" and slots == 1024:
        raise ValueError("D-OQ has no cell at 1,024 slots that is not loaded (section 7.1)")
    return f"{arm}|{slots}"


def unit_selection_cell(key: str, cfg: Mapping[str, Any] | None = None) -> tuple[int, int]:
    """The selection cell of a unit (section 7.1 table)."""
    arm, tail = key.split("|")
    c = cfg_of(cfg)
    for f, n in (*grid_cells(c), saturation_only_cell(c), *r2_cells(c)):
        if cell_name(f, n) == tail and (arm == "R2" or is_ladder_cell(f, n, c)):
            return f, n
    return {"1024": (2048, 1024), "4096": (8192, 4096), "16384": (32768, 16384)}[tail]


def unit_is_loaded(key: str, cfg: Mapping[str, Any] | None = None) -> bool:
    """A loaded-cell unit (a ladder cell's own unit): read at 65,536 updates."""
    arm, tail = key.split("|")
    return arm != "R2" and "/" in tail


def units(cfg: Mapping[str, Any] | None = None, *, sat256: bool = True) -> list[str]:
    """Every rate unit: 14 not loaded (F-OQ, T-OQ, H8 at three sizes; D-OQ at two; R2 at three) and 9 loaded-cell units (F-OQ, T-OQ, H8, D-OQ at both loaded cells; F-OQ at 2K/256)."""
    c = cfg_of(cfg)
    out: list[str] = []
    for arm in ARMS:
        for f, n in arm_cells(arm, c, sat256=sat256):
            k = unit_key(arm, f, n, c)
            if k not in out:
                out.append(k)
    return out


def unit_row(key: str, cfg: Mapping[str, Any] | None = None) -> int:
    """The row (facts) of a unit's selection cell."""
    return unit_selection_cell(key, cfg)[0]


# --- the ladder (section 7.2) ------------------------------------------------------------------------------------------------------------
def ladder_points(upto: int, cfg: Mapping[str, Any] | None = None) -> list[int]:
    """65,536 x {1, 1.5, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, ...} (alternating x1.5 and x4/3) up to ``upto``: 32,768 x (2^j, j >= 1) and 32,768 x (3 x 2^j, j >= 0)."""
    half = int(cfg_of(cfg)["ladder"]["half_unit"])
    base = int(cfg_of(cfg)["ladder"]["base"])
    out: set[int] = set()
    j = 0
    while True:
        for f in (2 << j, 3 << j):
            v = half * f
            if v >= base and v <= upto:
                out.add(v)
        if half * (2 << j) > upto:
            break
        j += 1
    return sorted(out)


def is_ladder_point(u: int, cfg: Mapping[str, Any] | None = None) -> bool:
    return u in ladder_points(max(u, 1), cfg)


def levels_above(u0: int, cfg: Mapping[str, Any] | None = None) -> list[int]:
    """The first ``levels`` ladder points above U0 (the fourth is always 4 x U0): 1.333, 2, 2.667, 4 x U0 for a U0 of P10-S1's form (393,216; 786,432), 1.5, 2, 3, 4 x U0 for a power of two times 65,536."""
    n = int(cfg_of(cfg)["ladder"]["levels"])
    if not is_ladder_point(u0, cfg):
        raise ValueError(f"U0 = {u0} is not a ladder point")
    pts = [p for p in ladder_points(4 * u0 + 1, cfg) if p > u0][:n]
    if len(pts) != n or pts[-1] != 4 * u0:
        raise ValueError(f"the ladder above {u0} does not end at 4 x U0")
    return pts


def doubling_snapshots(cfg: Mapping[str, Any] | None = None) -> list[int]:
    """The doubling grid from 512 below 32,768: 512, 1024, ..., 16384."""
    start = int(cfg_of(cfg)["ladder"]["doubling_from"])
    out, v = [], start
    while v < int(cfg_of(cfg)["ladder"]["half_unit"]):
        out.append(v)
        v *= 2
    return out


def multiple_of(u_p: int, m: float) -> int:
    v = u_p * m
    if v != int(v):
        raise ValueError(f"{m} x U_P = {v} is not an integer number of updates")
    return int(v)


def loaded_snapshots(u_p: int, granted: int, cfg: Mapping[str, Any] | None = None, *, doubling: Iterable[int] | None = None) -> list[int]:
    """Snapshots of a ladder cell up to its granted length (section 7.2 item 2): every ladder point and half of every ladder point up to ``granted``, the doubling grid from 512 below 32,768, and U_P x
    {1, 1.25, 1.5, 2, 2.5, 3, 4, 6} of the cell's row (the matched-compute reads need them)."""
    c = cfg_of(cfg)
    marks: set[int] = set(doubling if doubling is not None else doubling_snapshots(c))
    for p in ladder_points(granted, c):
        marks.add(p)
        marks.add(p // 2)
    for m in c["ladder"]["u_p_multiples"]:
        marks.add(multiple_of(u_p, float(m)))
    return sorted(x for x in marks if 1 <= x <= granted)


def grid_snapshots(u_p: int, run: int, cfg: Mapping[str, Any] | None = None) -> list[int]:
    """Snapshots of a cell that is not loaded (section 7.2): U_P x {1/16, 1/8, 1/4, 1/2, 1, 1.25, 1.5, 2, 2.5, 3, 4, 6} up to the run length (R2: up to U_P)."""
    marks = {int(u_p * f) for f in cfg_of(cfg)["ladder"]["snapshot_fractions"] if u_p * f == int(u_p * f) and 1 <= u_p * f <= run}
    marks.add(run)
    return sorted(m for m in marks if m >= 1)


def i_star(values: Mapping[int, float], limit: int) -> float:
    """The maximum of i over the snapshots at or below ``limit`` (never falls with further updates)."""
    eligible = [v for u, v in values.items() if u <= limit]
    if not eligible:
        raise ValueError(f"no snapshot at or below {limit}")
    return max(eligible)


def full_at(i_by_update: Mapping[str, Mapping[int, float]], u: int, previous: int, *, plateau_max: float, floor_i: float, i_max: float | None = None) -> bool:
    """Full at ladder point ``u`` (section 7.2 item 3), on every panel in ``i_by_update`` (panel -> {update: i}): i*(u) - i*(u/2) <= plateau_max and i*(u/2) >= floor_i, at two consecutive ladder points, of which ``u`` is the
    second (``previous`` is the first). ``i_max`` is the calibration's extra condition i*(u) <= 4.0 on every view. A panel lacking a snapshot needed makes the test False."""
    eps = 1e-12
    for series in i_by_update.values():
        for point in (previous, u):
            if point not in series or point // 2 not in series:
                return False
            hi, half = i_star(series, point), i_star(series, point // 2)
            if hi - half > plateau_max + eps or half < floor_i - eps:
                return False
            if i_max is not None and hi > i_max + eps:
                return False
    return True


# --- seeds (section 6) -------------------------------------------------------------------------------------------------------------
def registered_base(draw: int, cfg: Mapping[str, Any] | None = None) -> int:
    s = cfg_of(cfg)["seeds"]
    if not 1 <= draw <= int(s["registered_draws"]):
        raise ValueError("block M draws are 1..5")
    return int(s["registered_base"]) + int(s["registered_stride"]) * (draw - 1)


def init_seed_of(draw: int, cfg: Mapping[str, Any] | None = None) -> int:
    s = cfg_of(cfg)["seeds"]
    if not 1 <= draw <= int(s["registered_draws"]):
        raise ValueError("block M draws are 1..5")
    return int(s["init_base"]) + draw


def registered_seeds(draw: int, cfg: Mapping[str, Any] | None = None) -> Any:
    """P10-S1's in-set layout (``studies.p10s1.core.seed_set``) on block M's base of ``draw`` (index seed at base + 60)."""
    from studies.p10s1 import core as s1

    return s1.seed_set(f"p10is1-m-{draw}", registered_base(draw, cfg))


def calibration_seeds(k: int, cfg: Mapping[str, Any] | None = None) -> Any:
    from studies.p10s1 import core as s1

    if k not in (1, 2):
        raise ValueError("calibration draws are 1 and 2")
    return s1.seed_set(f"p10is1-cal-{k}", int(cfg_of(cfg)["seeds"]["calibration_bases"][k - 1]))


def calibration_init(k: int, cfg: Mapping[str, Any] | None = None) -> int:
    if k not in (1, 2):
        raise ValueError("calibration draws are 1 and 2")
    return int(cfg_of(cfg)["seeds"]["calibration_init"][k - 1])


def rehearsal_seeds(cfg: Mapping[str, Any] | None = None) -> Any:
    from studies.p10s1 import core as s1

    return s1.seed_set("p10is1-rehearsal", int(cfg_of(cfg)["seeds"]["rehearsal_base"]))


def test_seeds(k: int = 0, cfg: Mapping[str, Any] | None = None) -> Any:
    """Unit tests and test mode: sets at 933001 + 100 k (k = 0..8), inside the registry's test range."""
    from studies.p10s1 import core as s1

    s = cfg_of(cfg)["seeds"]
    base = int(s["test_base"]) + 100 * k
    if not 0 <= k <= 8 or base + 99 > int(s["test_top"]):
        raise ValueError("test seed set out of range (0..8)")
    return s1.seed_set(f"p10is1-test-{k}", base)


def seed_set_values(seeds: Any) -> frozenset[int]:
    from studies.p10s1 import core as s1

    return s1.set_values(seeds)


def seeds_for(mode: str, draw: int, cfg: Mapping[str, Any] | None = None) -> tuple[Any, int]:
    """(seed set, initialisation seed) of replicate ``draw`` in ``mode``: registered block M; rehearsal the rehearsal draw with its initialisation; test the test range."""
    c = cfg_of(cfg)
    if mode == REGISTERED:
        return registered_seeds(draw, c), init_seed_of(draw, c)
    if mode == REHEARSAL:
        return rehearsal_seeds(c), int(c["seeds"]["rehearsal_init"])
    if mode == TEST:
        return test_seeds(draw - 1, c), int(c["seeds"]["test_init"][0])
    raise ValueError(f"unknown mode {mode!r}")


# --- cells ---------------------------------------------------------------------------------------------------------------------------
def make_cell(mode: str, arm: str, facts: int, slots: int, draw: int, init_seed: int, *, u_p: int, run: int, lr: float, kind: str = "P") -> Any:
    """P10-S1's ``Cell`` (its ``make_cell``; the label format carries the initialisation seed, the row's U_P, the run length when not the default and the rate when not 0.003)."""
    from studies.p10s1 import core as s1

    return s1.make_cell(kind, arm, facts, slots, draw, init_seed, u_p=u_p, run_updates=run, lr=lr, test=mode != REGISTERED)


def r2_run(u_p: int, cfg: Mapping[str, Any] | None = None) -> int:
    return int(cfg_of(cfg)["ladder"]["r2_run_multiplier"]) * u_p


def grid_run(u_p: int, cfg: Mapping[str, Any] | None = None) -> int:
    return int(cfg_of(cfg)["ladder"]["run_multiplier"]) * u_p


@dataclass(frozen=True)
class PlanParams:
    """What the calibration and the budget fix (section 7, 17.1): U_P of each row, the rate of every unit, U0 and the granted length G of each ladder cell, and whether 2K/256 runs."""

    row_u_p: Mapping[int, int]
    rates: Mapping[str, float]
    u0: Mapping[str, int] = field(default_factory=dict)  # cell_name -> U0 of each ladder cell (2K/256 only when it runs)
    granted: Mapping[str, int] = field(default_factory=dict)  # cell_name -> G
    sat256: bool = True

    def to_json(self) -> dict[str, Any]:
        return {"row_u_p": {str(k): v for k, v in self.row_u_p.items()}, "rates": dict(self.rates), "u0": dict(self.u0), "granted": dict(self.granted), "sat256": self.sat256}

    @classmethod
    def from_json(cls, d: Mapping[str, Any]) -> "PlanParams":
        return cls({int(k): int(v) for k, v in d["row_u_p"].items()}, {k: float(v) for k, v in d["rates"].items()}, {k: int(v) for k, v in d["u0"].items()}, {k: int(v) for k, v in d["granted"].items()}, bool(d["sat256"]))


def cell_lr(params: PlanParams, arm: str, facts: int, slots: int, cfg: Mapping[str, Any] | None = None) -> float:
    return float(params.rates[unit_key(arm, facts, slots, cfg)])


def cell_run(params: PlanParams, arm: str, facts: int, slots: int, cfg: Mapping[str, Any] | None = None) -> int:
    """Run length of a planned cell: R2 U_P of its row; a ladder cell its granted length G; every other cell 6 U_P (section 7.2). A ladder cell's actual end is the whole cell's U_run (ruling 27)."""
    name = cell_name(facts, slots)
    if arm != "R2" and is_ladder_cell(facts, slots, cfg):
        return int(params.granted[name])
    u_p = params.row_u_p[facts]
    return r2_run(u_p, cfg) if arm == "R2" else grid_run(u_p, cfg)


def cell_snapshots(params: PlanParams, arm: str, facts: int, slots: int, cfg: Mapping[str, Any] | None = None) -> list[int]:
    u_p = params.row_u_p[facts]
    run = cell_run(params, arm, facts, slots, cfg)
    if arm != "R2" and is_ladder_cell(facts, slots, cfg):
        return loaded_snapshots(u_p, run, cfg)
    return grid_snapshots(u_p, run, cfg)


def planned_cells(params: PlanParams, mode: str, cfg: Mapping[str, Any] | None = None, *, draws: Iterable[int] = range(1, 6)) -> list[dict[str, Any]]:
    """Every trained cell of the registry for ``mode``: 31 configurations x five replicates (155; 150 without 2K/256). Dictionaries (JSON-able) with the label and everything a stage needs."""
    c = cfg_of(cfg)
    out: list[dict[str, Any]] = []
    for draw in draws:
        seeds, init = seeds_for(mode, draw, c)
        for arm in ARMS:
            for facts, slots in arm_cells(arm, c, sat256=params.sat256):
                run = cell_run(params, arm, facts, slots, c)
                lr = cell_lr(params, arm, facts, slots, c)
                u_p = params.row_u_p[facts]
                cell = make_cell(mode, arm, facts, slots, draw, init, u_p=u_p, run=run, lr=lr)
                ladder = arm != "R2" and is_ladder_cell(facts, slots, c)
                out.append({
                    "label": cell.label, "arm": arm, "facts": facts, "slots": slots, "draw": draw, "init_seed": init, "seed_name": seeds.name, "seed_base": seeds.facts, "u_p": u_p, "lr": lr, "run": run,
                    "ladder_cell": ladder, "u0": int(params.u0[cell_name(facts, slots)]) if ladder else None, "snapshots": cell_snapshots(params, arm, facts, slots, c), "unit": unit_key(arm, facts, slots, c), "mode": mode,
                })  # fmt: skip
    labels = [x["label"] for x in out]
    if len(set(labels)) != len(labels):
        raise ValueError("two planned cells share a label")
    return out


# --- keys (section 18) --------------------------------------------------------------------------------------------------------------
_READ_NAMES = READS


def read_key(label: str, update: int, read: str) -> str:
    """The registry key of one read of one snapshot of one cell. The read's name is part of it, so two reads of one cell can never share a key (the defect of ``studies/p10s1/analysis.py`` lines 167-169)."""
    if not label or update < 1 or read not in _READ_NAMES:
        raise ValueError(f"not a read key: {(label, update, read)!r}")
    return f"eval|{label}|u{update:08d}|{read}"


_KEY_RE = re.compile(r"^eval\|(?P<label>[^|]+)\|u(?P<update>\d{8,})\|(?P<read>main|ivf)$")


def parse_read_key(key: str) -> tuple[str, int, str]:
    m = _KEY_RE.match(key)
    if not m:
        raise ValueError(f"not a read key: {key!r}")
    return m["label"], int(m["update"]), m["read"]


def baseline_key(draw: int, facts: int) -> str:
    """The key of the no-memory baseline of a draw's fact set (DEP-c's ``b``); distinct from every read key."""
    return f"baseline|d{draw}|f{facts}"


def item_id(stage: str, label: str, update: int | None = None) -> str:
    if not stage or not label:
        raise ValueError("not an item")
    return f"{stage}|{label}" if update is None else f"{stage}|{label}|u{update:08d}"


# --- time, envelope, records, ledger ------------------------------------------------------------------------------------------------
def utc_stamp(now: datetime | None = None) -> str:
    return (now or datetime.now(UTC)).strftime("%Y%m%dT%H%M%S%fZ")


def envelope(kind: str) -> dict[str, Any]:
    if kind not in RECORD_KINDS:
        raise ValueError(f"unknown record kind {kind!r}")
    return {"kind": kind, "schema": SCHEMA, "study": STUDY}


def check_envelope(record: Mapping[str, Any], kind: str | None = None) -> None:
    if record.get("study") != STUDY or record.get("schema") != SCHEMA or record.get("kind") not in RECORD_KINDS:
        raise ValueError("P10IS1 record needs study, schema and a registered kind")
    if kind is not None and record.get("kind") != kind:
        raise ValueError(f"expected a {kind!r} record, got {record.get('kind')!r}")


def jsonable(v: Any) -> Any:
    """Plain JSON values: NaN and infinities become None (``write_json`` refuses them), tuples lists."""
    if isinstance(v, float):
        return v if math.isfinite(v) else None
    if isinstance(v, Mapping):
        return {str(k): jsonable(x) for k, x in v.items()}
    if isinstance(v, list | tuple | set | frozenset):
        return [jsonable(x) for x in (sorted(v) if isinstance(v, set | frozenset) else v)]
    return v


def write_record(path: Path, record: Mapping[str, Any], *, overwrite: bool = False) -> None:
    check_envelope(record)
    if path.exists() and not overwrite:
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, jsonable(dict(record)))


def read_record(path: Path, kind: str | None = None) -> dict[str, Any]:
    rec = read_json(path)
    if not isinstance(rec, dict):
        raise ValueError(f"not a P10IS1 record: {path}")
    check_envelope(rec, kind)
    return rec


class LedgerRefused(RuntimeError):
    """A stage cannot start: the total cap is spent."""


class Ledger:
    """Charged wall time of the study, appended to one JSON file that lives outside the repository or where git ignores it (never in a frozen file). The cap is a config value in hours."""

    def __init__(self, path: Path, total_seconds: float) -> None:
        if not math.isfinite(total_seconds) or total_seconds <= 0:
            raise ValueError("the cap must be a positive number of seconds")
        self.path, self.total_seconds = path, float(total_seconds)

    def entries(self) -> list[dict[str, Any]]:
        if not self.path.is_file():
            return []
        data = read_json(self.path)
        if not isinstance(data, dict) or data.get("study") != STUDY or data.get("kind") != "ledger":
            raise ValueError(f"not a P10IS1 ledger: {self.path}")
        return list(data["entries"])

    def charged(self, stage: str | None = None) -> float:
        return float(sum(float(e["seconds"]) for e in self.entries() if stage is None or e["stage"] == stage))

    def remaining(self) -> float:
        return max(0.0, self.total_seconds - self.charged())

    def require_room(self, stage: str) -> None:
        if self.remaining() <= 0:
            raise LedgerRefused(f"stage {stage}: the total cap of {self.total_seconds:.0f} s is spent; the stage is PAUSED and the extension is the human lead's")

    def charge(self, stage: str, run: str, seconds: float) -> None:
        entries = self.entries()
        entries.append({"stage": stage, "run": run, "seconds": max(0.0, float(seconds)), "utc": datetime.now(UTC).isoformat()})
        self.path.parent.mkdir(parents=True, exist_ok=True)
        write_json(self.path, {"study": STUDY, "kind": "ledger", "schema": SCHEMA, "total_seconds": self.total_seconds, "entries": entries})


def propose_cap_hours(charged_hours: float, projected_remaining_hours: float) -> float:
    """Section 15: a resource cap is set after the rehearsal as charged + 2 x projected remaining, rounded up to the hour."""
    if charged_hours < 0 or projected_remaining_hours < 0:
        raise ValueError("hours are not negative")
    return float(math.ceil(charged_hours + 2.0 * projected_remaining_hours - 1e-9))


def cap_hours(name: str, cfg: Mapping[str, Any] | None = None) -> float:
    c = cfg_of(cfg)["caps"]
    key = f"{name}_hours"
    if key not in c:
        raise ValueError(f"no cap named {name!r}")
    return float(c[key])


def caps_provisional(cfg: Mapping[str, Any] | None = None) -> bool:
    return bool(cfg_of(cfg)["caps"]["provisional"])
