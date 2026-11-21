# ruff: noqa: E501
"""P10IS0 shared contract (ADR-0023): the config (every threshold is read from ``configs/p10is0_overload.toml`` and nowhere else), cell types and the load grid, cells and their labels, seeds
(the programme-wide registry's values, read from the config), record kinds and IO, the charged-time ledger.

No torch is imported here. The ADR text is not a frozen input: ``spec_sha256`` is for provenance only (ADR-0029 style).

Status: implementation self-checked only. Not independent review, not Astra validation, not human approval. Nothing is frozen and no registered run is approved.
"""

import math
import re
import tomllib
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from arborlm.io import file_sha256, read_json, write_json

STUDY = "P10IS0"
FAMILY = "P10IS0_OVERLOAD"
SCHEMA = 1
SPEC = "docs/decisions/ADR-0023-p10-i-s0-addressing-and-overload.md"
CONFIG = Path("configs/p10is0_overload.toml")
FREEZE_DIR = Path("studies/p10is0/freeze")
PLAN = FREEZE_DIR / "plan.json"
FREEZE_RECORD = FREEZE_DIR / "freeze_record.json"
DURATIONS = FREEZE_DIR / "durations.json"
STAGE_CAPS = FREEZE_DIR / "stage_caps.json"
LAUNCH_DIR = Path("studies/p10is0/launch")

ARMS = ("A5-D", "A0", "A6")
LEARNED_ARMS = ("A5-D", "A0")
BATCH_FACTS = 128  # answer sites per update (updates = exposures x facts / 128)
SERIES = ("M", "S", "X")
ROLES = ("REG", "CAL", "REH", "CHK", "TEST")

RECORD_KINDS = (
    "train", "snapshot", "eval", "sealed_eval", "stage_manifest", "freeze_plan", "freeze_record", "analysis", "ledger", "rehearsal", "data_manifest", "gate", "identity_gate", "timing", "durations",
    "stage_caps", "engineering_stop", "report_manifest", "x8_addendum", "event",
)  # fmt: skip

# --- the config ----------------------------------------------------------------------------------------------------------------------
_REQUIRED: dict[str, tuple[str, ...]] = {
    "thresholds": (
        "success_fraction_of_a6", "heldout_fraction", "dependence_fraction", "a6_floor_anchor", "a6_floor_loaded", "stable_threshold", "max_failed_reliable", "max_not_evaluated_draws", "min_successes",
        "line_fail_cells", "plateau_step", "plateau_steps_required", "confirm_step", "t_factor", "paired_d", "paired_p", "reference_near_ceiling", "x8_trigger_load",
    ),
    "ladder": ("base", "extension_ceiling", "base_ceiling_t", "extended_ceiling_t", "extension_doublings"),
    "budget": ("b_hours", "workers", "stage_cap_factor", "x8_in_projection", "analysis_report_hours"),
    "grid": ("cell_types",),
    "draws": ("registered", "reserve", "calibration", "checkpoint_probe_every", "checkpoint_probe_every_late", "checkpoint_probe_switch", "first_readout_exposures"),
    "seeds": (
        "registered_base", "draw_stride", "reserve_bases", "calibration_bases", "rehearsal_base", "check_base", "repeat_cal_first", "repeat_cal_second", "repeat_stride", "repeat_count", "init_registered",
        "init_calibration", "init_rehearsal", "init_check", "test_init", "repeat_init_first", "repeat_init_second", "repeat_init_stride", "test_base", "test_top", "fact_set_offsets", "swap_offsets",
        "identity_gate_data_base", "identity_gate_init",
    ),
    "seed_ranges": ("registered", "auxiliary", "calibration", "rehearsal", "check", "spare", "init", "test", "checker", "checker_sha256"),
    "identity": ("tolerance", "long_updates", "p10s0_cadence", "fact_counts_a5d_a6", "fact_counts_a0", "end_to_end_slots"),
    "resources": (
        "rss_worker_bytes", "rss_aggregate_bytes", "memory_budget_bytes", "combined_aggregate_bytes", "memory_growth_mib", "disk_cap_bytes", "disk_free_min_bytes", "update_record_bytes",
        "disk_bytes_per_update", "eval_chunk_elements",
    ),
    "timing": ("quiet_load_max", "attempts", "attempt_window_hours", "min_updates", "busy_processes", "sample_seconds", "sample_window_seconds", "workers"),
    "platform": ("system", "machine", "torch", "torch_num_threads", "torch_interop_threads", "deterministic_algorithms"),
    "caps": ("provisional", "total_hours", "stage_r_hours"),
}  # fmt: skip


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def validate_config(data: Mapping[str, Any]) -> Mapping[str, Any]:
    """Every section and key must exist and every number must be finite; the nine cell types of section 4.1 must be present. Values are not compared with constants here: the config is the one place they live."""
    if data.get("schema_version") != SCHEMA or data.get("experiment_family") != FAMILY or data.get("spec_reference") != SPEC:
        raise ValueError("P10IS0 config: schema_version, experiment_family or spec_reference differ")
    for section, keys in _REQUIRED.items():
        block = data.get(section)
        if not isinstance(block, dict):
            raise ValueError(f"P10IS0 config: section [{section}] is missing")
        missing = [k for k in keys if k not in block]
        if missing:
            raise ValueError(f"P10IS0 config: [{section}] lacks {missing}")
    cts = data["grid"]["cell_types"]
    if not isinstance(cts, list) or len(cts) != 9:
        raise ValueError("P10IS0 config: [[grid.cell_types]] must list the nine cell types of section 4.1 (M 4, S 4, X8 1)")
    for c in cts:
        if set(c) != {"series", "facts", "slots", "arms"} or c["series"] not in SERIES or not set(c["arms"]) <= set(ARMS):
            raise ValueError(f"P10IS0 config: bad cell type {c!r}")

    def walk(v: Any) -> None:
        if isinstance(v, float) and not math.isfinite(v):
            raise ValueError("P10IS0 config: a non-finite number")
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
    """Provenance only: the ADR text is not in the frozen-input set (section 14)."""
    return file_sha256((root or repo_root()) / SPEC)


@dataclass(frozen=True)
class Thresholds:
    """Every scientific threshold, read from the config."""

    success_fraction_of_a6: float
    heldout_fraction: float
    dependence_fraction: float
    a6_floor_anchor: float
    a6_floor_loaded: float
    stable_threshold: float
    max_failed_reliable: int
    max_not_evaluated_draws: int
    min_successes: int
    line_fail_cells: int
    plateau_step: float
    plateau_steps_required: int
    confirm_step: float
    t_factor: int
    paired_d: int
    paired_p: float
    reference_near_ceiling: float
    x8_trigger_load: float

    @classmethod
    def from_config(cls, cfg: Mapping[str, Any] | None = None) -> "Thresholds":
        t = (cfg or load_config())["thresholds"]
        ints = {"max_failed_reliable", "max_not_evaluated_draws", "min_successes", "line_fail_cells", "plateau_steps_required", "t_factor", "paired_d"}
        return cls(**{f: (int(t[f]) if f in ints else float(t[f])) for f in cls.__dataclass_fields__})


# --- sizes, cell types, the load grid (section 4.1) ----------------------------------------------------------------------------------------
def size_name(n: int) -> str:
    return f"{n // 1024}K" if n % 1024 == 0 else str(n)


def updates_for(exposures: int, facts: int) -> int:
    """Updates = exposures per fact x facts / 128 (512 exposures = 8,192 updates at 2,048 facts and 32,768 at 8,192)."""
    if (exposures * facts) % BATCH_FACTS:
        raise ValueError("exposures x facts must be a multiple of 128")
    return exposures * facts // BATCH_FACTS


def exposures_for(updates: int, facts: int) -> float:
    return updates * BATCH_FACTS / facts


@dataclass(frozen=True)
class CellType:
    """One (facts, slots) pair of a series. ``load`` is facts per slot. Names are unique across series (``8K/16K``, ``2K/512``)."""

    series: str
    facts: int
    slots: int
    arms: tuple[str, ...]

    @property
    def name(self) -> str:
        return f"{size_name(self.facts)}/{size_name(self.slots)}"

    @property
    def load(self) -> float:
        return self.facts / self.slots

    @property
    def anchor(self) -> bool:
        return self.load == 0.5

    @property
    def conditional(self) -> bool:
        return self.series == "X"

    def floor(self, thresholds: Thresholds) -> float:
        """The cell type's evaluability floor for A6 (0.90 at load 0.5; 0.50 at loads of 1 and above)."""
        return thresholds.a6_floor_anchor if self.load <= 0.5 else thresholds.a6_floor_loaded

    def updates(self, exposures: int) -> int:
        return updates_for(exposures, self.facts)


def cell_types(cfg: Mapping[str, Any] | None = None, *, include_x8: bool = False) -> list[CellType]:
    c = cfg or load_config()
    out = [CellType(x["series"], int(x["facts"]), int(x["slots"]), tuple(x["arms"])) for x in c["grid"]["cell_types"]]
    return [ct for ct in out if include_x8 or not ct.conditional]


def cell_type_by_name(name: str, cfg: Mapping[str, Any] | None = None) -> CellType:
    for ct in cell_types(cfg, include_x8=True):
        if ct.name == name:
            return ct
    raise ValueError(f"unknown cell type {name!r}")


def loads_of(cfg: Mapping[str, Any] | None = None, *, include_x8: bool = False) -> list[float]:
    return sorted({ct.load for ct in cell_types(cfg, include_x8=include_x8)})


def order_of_candidates(cts: Iterable[CellType]) -> list[CellType]:
    """Ascending load, series M before S at equal load (section 5.1 item 4)."""
    rank = {"M": 0, "S": 1, "X": 2}
    return sorted(cts, key=lambda ct: (ct.load, rank[ct.series]))


# --- cells and labels ----------------------------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Cell:
    """One run. ``role``: REG (registered or reserve draw), CAL (a calibration draw of Stage R or X8's), REH (rehearsal or pipeline-check data), CHK (identity or end-to-end gate), TEST (unit tests).
    ``draw`` is the registered draw 1..10 (or the calibration draw 1..2, or 1 for single-draw roles). ``attempt`` numbers a repeated Stage R (0 = the first)."""

    role: str
    series: str
    arm: str
    facts: int
    slots: int
    draw: int
    init_seed: int
    attempt: int = 0

    def __post_init__(self) -> None:
        if self.role not in ROLES or self.series not in SERIES or self.arm not in ARMS or self.facts <= 0 or self.slots <= 0 or self.draw < 0 or self.facts % BATCH_FACTS:
            raise ValueError(f"unregistered P10IS0 cell: {self.label_unchecked()}")

    def label_unchecked(self) -> str:
        return f"{self.role}-{self.series}-{self.arm}-{size_name(self.facts)}-{size_name(self.slots)}-d{self.draw:02d}-i{self.init_seed}" + (f"-r{self.attempt}" if self.attempt else "")

    @property
    def label(self) -> str:
        """The key of one run: role, series, arm, sizes, draw, initialisation seed and attempt, so two records never share a key."""
        return self.label_unchecked()

    @property
    def stage(self) -> int:  # p9ii's evaluate reads ``cell.stage`` for its record; this study has no stages of P9-II's kind
        return 1

    @property
    def seed_index(self) -> int:
        return 0

    @property
    def load(self) -> float:
        return self.facts / self.slots

    @property
    def learned(self) -> bool:
        return self.arm in LEARNED_ARMS


# --- seeds (section 4.2; every value is the registry's, read from the config) -------------------------------------------------------------------
@dataclass(frozen=True)
class SetSpec:
    """A named set of seed blocks: ``base`` + the fact-set offset (+0..19: P9's fourteen data seeds, Panel A null seeds +14..16, Panel B's +17..19; P10-S0's layout)."""

    name: str
    base: int

    def block(self, facts: int, cfg: Mapping[str, Any] | None = None) -> Any:
        from studies.p10s0 import core as s0core

        offsets = (cfg or load_config())["seeds"]["fact_set_offsets"]
        if str(facts) not in offsets:
            raise ValueError(f"no fact-set offset for {facts} facts (the 32,768-fact set is not generated: ruling 9)")
        return s0core.block_seeds(self.name, self.base, facts)

    def swap_seed(self, facts: int, cfg: Mapping[str, Any] | None = None) -> int:
        return self.base + int((cfg or load_config())["seeds"]["swap_offsets"][str(facts)])

    def values(self, cfg: Mapping[str, Any] | None = None) -> frozenset[int]:
        c = cfg or load_config()
        out: set[int] = set()
        for f in (int(k) for k in c["seeds"]["fact_set_offsets"]):
            s = self.block(f, c)
            out |= {*s.data_values(), *s.null_seeds_a, *s.null_seeds_b}
        out |= {self.base + int(o) for o in c["seeds"]["swap_offsets"].values()}
        return frozenset(out)


PROFILES = ("registered", "test")


def _profiled(spec: SetSpec, idx: int, cfg: Mapping[str, Any], profile: str) -> SetSpec:
    """The test profile (stage 2's pipeline rehearsal, the synthetic tiny configuration): the same names on test-range bases (932001 + 4 idx; these sets overlap one another and are never used for a result). Registered values are
    never read under it."""
    if profile == "registered":
        return spec
    if profile != "test":
        raise ValueError(f"unknown profile {profile!r}")
    return SetSpec(spec.name, int(cfg["seeds"]["test_base"]) + 4 * idx)


def registered_set(draw: int, cfg: Mapping[str, Any] | None = None, profile: str = "registered") -> SetSpec:
    c = (cfg or load_config())
    if not 1 <= draw <= int(c["draws"]["registered"]):
        raise ValueError("registered draws are 1..10")
    s = c["seeds"]
    return _profiled(SetSpec(f"p10is0-draw-{draw}", int(s["registered_base"]) + int(s["draw_stride"]) * (draw - 1)), draw - 1, c, profile)


def reserve_set(k: int, cfg: Mapping[str, Any] | None = None, profile: str = "registered") -> SetSpec:
    c = cfg or load_config()
    bases = c["seeds"]["reserve_bases"]
    if not 1 <= k <= len(bases):
        raise ValueError("reserve draws are 1..4")
    return _profiled(SetSpec(f"p10is0-reserve-{k}", int(bases[k - 1])), 10 + k - 1, c, profile)


def set_of_name(name: str, cfg: Mapping[str, Any] | None = None, profile: str = "registered") -> SetSpec:
    """The seed set a plan names (``p10is0-draw-k`` or ``p10is0-reserve-k``)."""
    m = re.fullmatch(r"p10is0-(draw|reserve)-(\d+)", name)
    if m is None:
        raise ValueError(f"not a draw or reserve set name: {name!r}")
    return registered_set(int(m[2]), cfg, profile) if m[1] == "draw" else reserve_set(int(m[2]), cfg, profile)


def calibration_set(draw: int, attempt: int = 0, cfg: Mapping[str, Any] | None = None, profile: str = "registered") -> SetSpec:
    """Calibration draw 1 or 2 of the original Stage R (attempt 0) or of repeat ``attempt`` = 1..3 (the registry's spare values)."""
    c = cfg or load_config()
    s = c["seeds"]
    if draw not in (1, 2):
        raise ValueError("calibration draws are 1 and 2")
    if attempt == 0:
        return _profiled(SetSpec(f"p10is0-cal-{draw}", int(s["calibration_bases"][draw - 1])), 14 + draw - 1, c, profile)
    if not 1 <= attempt <= int(s["repeat_count"]):
        raise ValueError("a fourth repeat has no allocated values: an engineering stop until the human lead rules")
    first, second = int(s["repeat_cal_first"]), int(s["repeat_cal_second"])
    return _profiled(SetSpec(f"p10is0-cal-{draw}-repeat-{attempt}", (first if draw == 1 else second) + int(s["repeat_stride"]) * (attempt - 1)), 14 + 2 * attempt + draw - 1, c, profile)


def rehearsal_set(cfg: Mapping[str, Any] | None = None, profile: str = "registered") -> SetSpec:
    c = cfg or load_config()
    return _profiled(SetSpec("p10is0-rehearsal", int(c["seeds"]["rehearsal_base"])), 22, c, profile)


def check_set(cfg: Mapping[str, Any] | None = None, profile: str = "registered") -> SetSpec:
    c = cfg or load_config()
    return _profiled(SetSpec("p10is0-check", int(c["seeds"]["check_base"])), 23, c, profile)


def test_set(k: int = 0, cfg: Mapping[str, Any] | None = None) -> SetSpec:
    """Unit tests: 932001 + 100 k, k = 0..8 (the registry's test range)."""
    s = (cfg or load_config())["seeds"]
    base = int(s["test_base"]) + 100 * k
    if not 0 <= k <= 8 or base + 99 > int(s["test_top"]):
        raise ValueError("test seed set out of range (0..8)")
    return SetSpec(f"p10is0-test-{k}", base)


def init_seed(role: str, arm: str, draw: int, attempt: int = 0, cfg: Mapping[str, Any] | None = None, profile: str = "registered") -> int:
    """Initialisation seeds by role (section 4.2): registered 330001 (A5-D and A0 on odd draws; A6 on every draw) and 330002 (A5-D and A0 on even draws); calibration 330091 and 330093 (330061 + 2 (k-1) and 330062 + 2 (k-1) in repeats);
    rehearsal and pipeline check 330092; test mode 330098 and 330099."""
    c = cfg or load_config()
    s = c["seeds"]
    if profile == "test":
        return int(s["test_init"][draw % 2])  # the test profile takes the named test-mode initialisations only
    if role == "REG":
        return int(s["init_registered"][0]) if (arm == "A6" or draw % 2 == 1) else int(s["init_registered"][1])
    if role == "CAL":
        if draw not in (1, 2):
            raise ValueError("calibration draws are 1 and 2")
        if attempt == 0:
            return int(s["init_calibration"][draw - 1])
        base = int(s["repeat_init_first"] if draw == 1 else s["repeat_init_second"])
        return base + int(s["repeat_init_stride"]) * (attempt - 1)
    if role == "REH":
        return int(s["init_rehearsal"])
    if role == "CHK":
        return int(s["init_check"])
    if role == "TEST":
        return int(s["test_init"][draw % 2])
    raise ValueError(f"unknown role {role!r}")


def set_for(role: str, draw: int, attempt: int = 0, cfg: Mapping[str, Any] | None = None, profile: str = "registered") -> SetSpec:
    if role == "REG":
        return registered_set(draw, cfg, profile)
    if role == "CAL":
        return calibration_set(draw, attempt, cfg, profile)
    if role == "REH":
        return rehearsal_set(cfg, profile)
    if role == "CHK":
        return check_set(cfg, profile)
    if role == "TEST":
        return test_set(draw, cfg)
    raise ValueError(f"unknown role {role!r}")


def make_cell(role: str, ct: CellType, arm: str, draw: int, attempt: int = 0, cfg: Mapping[str, Any] | None = None, profile: str = "registered") -> Cell:
    return Cell(role, ct.series, arm, ct.facts, ct.slots, draw, init_seed(role, arm, draw, attempt, cfg, profile), attempt)


def registered_cells(cfg: Mapping[str, Any] | None = None, *, include_x8: bool = False, profile: str = "registered") -> list[Cell]:
    """The main grid: 120 cells of series M, 80 of series S (and 30 of X8 when ``include_x8``)."""
    c = cfg or load_config()
    out: list[Cell] = []
    for ct in cell_types(c, include_x8=include_x8):
        for arm in ct.arms:
            for d in range(1, int(c["draws"]["registered"]) + 1):
                out.append(make_cell("REG", ct, arm, d, 0, c, profile))
    return out


# --- time, envelope, records, ledger -----------------------------------------------------------------------------------------------------------
def utc_stamp(now: datetime | None = None) -> str:
    return (now or datetime.now(UTC)).strftime("%Y%m%dT%H%M%S%fZ")


def envelope(kind: str) -> dict[str, Any]:
    if kind not in RECORD_KINDS:
        raise ValueError(f"unknown record kind {kind!r}")
    return {"kind": kind, "schema": SCHEMA, "study": STUDY}


def check_envelope(record: Mapping[str, Any], kind: str | None = None) -> None:
    if record.get("study") != STUDY or record.get("schema") != SCHEMA or record.get("kind") not in RECORD_KINDS:
        raise ValueError("P10IS0 record needs study, schema and a registered kind")
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
        raise ValueError(f"not a P10IS0 record: {path}")
    check_envelope(rec, kind)
    return rec


class LedgerRefused(RuntimeError):
    """A stage cannot start: the cap is spent."""


class Ledger:
    """Charged wall time of the study (rehearsals and every registered stage) appended to one JSON file. It is never written inside the worktree during a registered run: the run directory is outside the
    repository or git-ignored (``assert_run_dir_ignored``)."""

    def __init__(self, path: Path, total_seconds: float) -> None:
        if not math.isfinite(total_seconds) or total_seconds <= 0:
            raise ValueError("the cap must be a positive number of seconds")
        self.path, self.total_seconds = path, float(total_seconds)

    def entries(self) -> list[dict[str, Any]]:
        if not self.path.is_file():
            return []
        data = read_json(self.path)
        if not isinstance(data, dict) or data.get("study") != STUDY or data.get("kind") != "ledger":
            raise ValueError(f"not a P10IS0 ledger: {self.path}")
        return list(data["entries"])

    def charged(self, stage: str | None = None, *, group: str | None = None) -> float:
        return float(sum(float(e["seconds"]) for e in self.entries() if (stage is None or e["stage"] == stage) and (group is None or e.get("group") == group)))

    def remaining(self) -> float:
        return max(0.0, self.total_seconds - self.charged())

    def require_room(self, stage: str) -> None:
        if self.remaining() <= 0:
            raise LedgerRefused(f"stage {stage}: the cap of {self.total_seconds:.0f} s is spent; the stage is PAUSED and an extension is the human lead's, on cost projections only")

    def charge(self, stage: str, run: str, seconds: float, group: str | None = None) -> None:
        entries = self.entries()
        entries.append({"stage": stage, "run": run, "seconds": max(0.0, float(seconds)), "utc": datetime.now(UTC).isoformat(), "group": group or stage})
        self.path.parent.mkdir(parents=True, exist_ok=True)
        write_json(self.path, {"study": STUDY, "kind": "ledger", "schema": SCHEMA, "total_seconds": self.total_seconds, "entries": entries})


def assert_run_dir_ignored(run_dir: Path, repo: Path | None = None) -> None:
    """The run directory must be outside the repository or git-ignored: a ledger or record written inside a tracked tree dirties it (the P10-S1 lesson). Uses ``git check-ignore``."""
    import subprocess

    root = (repo or repo_root()).resolve()
    run = run_dir.resolve()
    try:
        run.relative_to(root)
    except ValueError:
        return
    proc = subprocess.run(["git", "-C", str(root), "check-ignore", "-q", str(run)], check=False, capture_output=True)  # noqa: S603, S607
    if proc.returncode != 0:
        raise ValueError(f"run directory {run} is inside the repository and not git-ignored")


def hours(seconds: float) -> float:
    return seconds / 3600.0


def median(values: Sequence[Any]) -> Any:
    """The mean of the two middle values for an even count (P9's ``median``; ruling 5). Works on Fractions as well as floats."""
    if not values:
        raise ValueError("median of nothing")
    s = sorted(values)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2
