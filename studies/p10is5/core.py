# ruff: noqa: E501
"""P10IS5 shared contract (ADR-0028, engineering part only): the config (``configs/p10is5_ssd.toml``, the one place every threshold lives), the registered label strings, record kinds and record IO, seed
derivation, the statistics rules of ruling 10, and the exceptions that carry PAUSED and ENGINEERING STOP.

Nothing here touches a device, a file of the study or torch. The ADR text is not a frozen input: ``spec_sha256`` is for provenance only. Seeds are never used here; they are carried as data.
"""

import contextlib
import hashlib
import math
import tomllib
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from arborlm.io import file_sha256, read_json, write_json

STUDY = "P10IS5"
FAMILY = "P10IS5_SSD_COST_MODEL"
SCHEMA = 1
SPEC = "docs/decisions/ADR-0028-p10-i-s5-physical-ssd-memory.md"
CONFIG = Path("configs/p10is5_ssd.toml")
FREEZE_DIR = Path("studies/p10is5/freeze")
PLAN = FREEZE_DIR / "plan.json"
LAUNCH_DIR = Path("studies/p10is5/launch")

KINDS = (
    "freeze_plan", "freeze_record", "pass", "block", "stage_manifest", "r0", "r1", "cold_check", "prediction", "prediction_manifest", "harness_figure", "ec3", "rehearsal", "analysis", "report_manifest",
    "engineering_stop", "amendment", "write_ledger", "hours_ledger", "hygiene", "quiet",
)  # fmt: skip

# --- registered strings (sections 1, 5, 7, 9; spelled exactly) ------------------------------------------------------------------------------
EQ_A_OK, EQ_A_NOT = "BYTES CONFIRMED EXACTLY", "BYTES NOT CONFIRMED"
EQ_B_CHEAPER, EQ_B_PROPORTIONAL, EQ_B_DEARER, EQ_B_NOT_SEPARATED = "CONTIGUOUS REQUEST CHEAPER PER PAGE", "COST PROPORTIONAL TO PAGES", "CONTIGUOUS REQUEST DEARER PER PAGE", "NOT SEPARATED AT MARGIN"
EQ_D_OK = "COST TABLE REGISTERED"
ENG_NOT_EVALUABLE = "ENGINEERING NOT EVALUABLE"
SCI_LABEL = "SCIENTIFIC NOT EVALUABLE (PREREQUISITES NOT MET)"
SCI_REASONS = (
    "No approved learned-address capacity line: Q2 has no approved source; ADR-0024's lane L is unspecified and not approved, so no outcome of the programme can satisfy Q2.",
    "The largest licensed cell is about 3 MB: ADR-0023 licenses learned addressing only at tested cell types with load at most L_Q, the largest has 16,384 slots, 16,384 x 192 bytes = 3,145,728 bytes, so Q1, Q2 and Q3 can be true together only if RAM is restricted by construction.",
)  # fmt: skip
ARITHMETIC_HEADING = "ARITHMETIC ONLY — NOT MEASURED — NOT A READ PATH"
STORE_PAGES_CACHED, COUNTER_CONTAMINATED = "STORE PAGES CACHED", "COUNTER CONTAMINATED"
HARNESS_LIMITED = "HARNESS-LIMITED"
HARNESS_NOT_MEASURED = "HARNESS FIGURE NOT MEASURED"
NOT_READABLE = "NOT READABLE"
NOT_CHECKABLE = "NOT CHECKABLE WITHOUT ADMINISTRATOR ACCESS"
STORE_NOT_COLD = "PAUSED — STORE NOT COLD"
STORE_CANNOT_BE_HELD_COLD = "STORE CANNOT BE HELD COLD"
STORE_RETAINED = "STORE RETAINED BY SNAPSHOT"
PAUSED_IDENTITY = "PAUSED — IDENTITY"
# NOT EVALUABLE reasons, in the order of section 9 (the first failing one is the label; all failing ones are printed).
REASONS_ORDER = (
    "NO PHYSICAL COUNTER", "CACHE NOT DEFEATED", "POSITIVE CONTROL FAILED", "STORE CANNOT BE HELD COLD", "TIMING SPREAD", "MACHINE NOT QUIET", "FEWER THAN FOUR VALID REPEATS", "WRITE BUDGET EXHAUSTED",
)  # fmt: skip
GENERAL_REASONS = ("NO PHYSICAL COUNTER", "CACHE NOT DEFEATED", "POSITIVE CONTROL FAILED", "STORE CANNOT BE HELD COLD", "WRITE BUDGET EXHAUSTED")
IDENTITY_EXIT = 75  # a refusal on an identity or precondition check: PAUSED — IDENTITY, nothing written; restoring the file resumes the task
ENGINEERING_STOP_EXIT = 70
PAUSED_EXIT = 76


class StageRefused(RuntimeError):
    """A registered entry point refuses (no plan, no freeze, no Decision 2, a dirty tree, an identity that differs)."""


class IdentityRefused(StageRefused):
    """A registered entry point refused on an identity or precondition check: exit 75, PAUSED — IDENTITY, nothing written."""


FINAL_STATUSES = (
    "COMPLETE", "ENGINEERING NOT EVALUABLE — STORE CANNOT BE HELD COLD", "ENGINEERING NOT EVALUABLE — MACHINE NOT QUIET", "ENGINEERING NOT EVALUABLE — WRITE BUDGET EXHAUSTED",
)  # fmt: skip
STATUS_MACHINE_NOT_QUIET, STATUS_WRITE_BUDGET, STATUS_COLD = FINAL_STATUSES[2], FINAL_STATUSES[3], FINAL_STATUSES[1]
STAGE_GROUP = {"R0": "rehearsal", "R1": "rehearsal", "M": "rehearsal", "K": "rehearsal", "E1": "e1", "P": "e1", "E2": "e2", "analysis": "e2"}


class Paused(RuntimeError):
    """A resumable stop (write cap, quiet rule, free space, drive health, store not cold). ``reason`` is the registered text."""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason, self.detail = reason, detail


class EngineeringStop(RuntimeError):
    """A code error, an environment error or a non-finite value: ENGINEERING STOP (cause). Never a scientific NOT EVALUABLE (ADR-0028 section 9)."""

    def __init__(self, cause: str, detail: str = "") -> None:
        super().__init__(f"ENGINEERING STOP ({cause}): {detail}" if detail else f"ENGINEERING STOP ({cause})")
        self.cause, self.detail = cause, detail


class WriteBudgetExceeded(Paused):
    """A write that would pass the 10 GB cap is refused before it is made (PAUSED, resumable)."""

    def __init__(self, detail: str = "") -> None:
        super().__init__("PAUSED — WRITE BUDGET", detail)


# --- config ---------------------------------------------------------------------------------------------------------------------------------
def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


_REQUIRED: dict[str, tuple[str, ...]] = {
    "device": ("page_bytes", "tile_pages", "store_tiles", "rehearsal_tiles", "control_tiles", "rehearsal_usable_tiles", "band_start_tile", "f_rdahead", "f_nocache", "f_fullfsync", "write_unit_bytes", "build_chunk_bytes", "directory_suffix"),
    "cells": ("sizes", "depths", "requests_per_pass", "tiles_per_pass", "rehearsal_requests_per_pass", "rehearsal_tiles_per_pass", "repeats", "spare_repeat", "r1_depths", "r1_reread_working_set_tiles"),
    "thresholds": ("m_floor", "m_ceiling", "m_cv_multiple", "label_min_repeats", "valid_min_repeats", "harness_limited_fraction", "harness_requests", "harness_tiles", "harness_depths"),
    "budget": ("cap_bytes", "probe_bytes", "control_file_bytes", "rehearsal_file_bytes", "store_file_bytes", "free_space_min_bytes", "max_builds_per_file"),
    "quiet": ("load_margin", "idle_window_seconds", "idle_interval_seconds", "idle_samples", "retry_interval_seconds", "retry_deadline_seconds", "settle_seconds", "activity_window_seconds", "percentile", "hid_idle_min_seconds", "cold_wait_seconds", "extra_sessions", "pass_timeout_seconds", "process_markers"),
    "fixed_after_r1_and_m": ("provisional", "m_t", "timing_spread", "load_p95", "read_bytes_per_s_p95", "write_bytes_per_s_p95", "read_ops_per_s_p95", "write_ops_per_s_p95"),
    "caps": ("provisional", "rehearsal_hours", "e1_hours", "e2_hours", "total_hours"),
    "resources": ("memory_guard_bytes",),
    "platform": ("system", "machine", "torch", "torch_num_threads", "torch_interop_threads", "deterministic_algorithms", "python_prefix"),
    "seeds": ("store_contents", "r1_rehearsal_file_contents", "r1_control_file_contents", "request_order", "spare_request_order", "r1_request_order", "m_request_order", "k_request_order", "pass_order", "spare_pass_order", "r1_pass_order", "m_pass_order", "k_pass_order", "tile_assignment", "m_tile_assignment", "k_tile_assignment", "r1_reread_offsets", "test_range"),
    "seed_ranges": ("registered", "auxiliary", "r1", "rehearsal", "test", "checker", "checker_sha256"),
}  # fmt: skip


def validate_config(data: Mapping[str, Any]) -> Mapping[str, Any]:
    """Every section and key must exist; numbers must be finite; the grid must be 4 sizes by 6 depths with one n(s) per size. Values are not compared to constants here: the config is the one place they live."""
    if data.get("schema_version") != SCHEMA or data.get("experiment_family") != FAMILY or data.get("spec_reference") != SPEC:
        raise ValueError("P10IS5 config: schema_version, experiment_family or spec_reference differ")
    for section, keys in _REQUIRED.items():
        block = data.get(section)
        if not isinstance(block, dict):
            raise ValueError(f"P10IS5 config: section [{section}] is missing")
        missing = [k for k in keys if k not in block]
        if missing:
            raise ValueError(f"P10IS5 config: [{section}] lacks {missing}")
    c = data["cells"]
    for key in ("requests_per_pass", "tiles_per_pass", "rehearsal_requests_per_pass", "rehearsal_tiles_per_pass"):
        if len(c[key]) != len(c["sizes"]):
            raise ValueError(f"P10IS5 config: [cells].{key} needs one value per size")
    if len(data["seeds"]["request_order"]) != int(c["repeats"]) or len(data["seeds"]["pass_order"]) != int(c["repeats"]):
        raise ValueError("P10IS5 config: one request-order and one pass-order seed per repeat")

    def walk(v: Any) -> None:
        if isinstance(v, float) and not math.isfinite(v):
            raise ValueError("P10IS5 config: a non-finite number")
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
    """Provenance only: the ADR text is not in the frozen-input set (section 12)."""
    return file_sha256((root or repo_root()) / SPEC)


def provisional_figures(cfg: Mapping[str, Any]) -> bool:
    return bool(cfg["fixed_after_r1_and_m"]["provisional"])


def caps_provisional(cfg: Mapping[str, Any]) -> bool:
    return bool(cfg["caps"]["provisional"])


def cap_hours(stage_name: str, cfg: Mapping[str, Any]) -> float:
    key = f"{stage_name}_hours"
    if key not in cfg["caps"]:
        raise ValueError(f"no cap named {stage_name!r}")
    return float(cfg["caps"][key])


def propose_cap_hours(charged_hours: float, projected_remaining_hours: float) -> float:
    """Section 8: charged hours so far + 2 x projected remaining (ADR-0029's rule). Printed for the lead; nothing writes the config."""
    if charged_hours < 0 or projected_remaining_hours < 0:
        raise ValueError("hours are not negative")
    return charged_hours + 2.0 * projected_remaining_hours


# --- geometry values ---------------------------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Geometry:
    """One file's pass geometry: which tiles the permutation covers, requests and tiles per pass for each size, and the repeats (registered: 5 and the spare; rehearsal: 5, no spare)."""

    name: str
    file_tiles: int
    usable_tiles: int
    sizes: tuple[int, ...]
    depths: tuple[int, ...]
    requests: tuple[int, ...]
    tiles: tuple[int, ...]
    repeats: int
    has_spare: bool

    @property
    def n_of(self) -> dict[int, int]:
        return dict(zip(self.sizes, self.requests, strict=True))

    @property
    def tiles_of(self) -> dict[int, int]:
        return dict(zip(self.sizes, self.tiles, strict=True))

    @property
    def tiles_per_repeat_depth(self) -> int:
        return sum(self.tiles)

    @property
    def all_repeats(self) -> tuple[int, ...]:
        return tuple(range(1, self.repeats + (1 if self.has_spare else 0) + 1))

    def cells(self) -> list[tuple[int, int]]:
        """The 24 cells, k-major (ruling 3): (k, s)."""
        return [(k, s) for k in self.depths for s in self.sizes]

    def tiles_needed(self) -> int:
        return len(self.all_repeats) * len(self.depths) * self.tiles_per_repeat_depth


def registered_geometry(cfg: Mapping[str, Any]) -> Geometry:
    c, d = cfg["cells"], cfg["device"]
    return Geometry("registered", int(d["store_tiles"]), int(d["store_tiles"]), tuple(map(int, c["sizes"])), tuple(map(int, c["depths"])), tuple(map(int, c["requests_per_pass"])), tuple(map(int, c["tiles_per_pass"])), int(c["repeats"]), True)


def rehearsal_geometry(cfg: Mapping[str, Any]) -> Geometry:
    c, d = cfg["cells"], cfg["device"]
    return Geometry("rehearsal", int(d["rehearsal_tiles"]), int(d["rehearsal_usable_tiles"]), tuple(map(int, c["sizes"])), tuple(map(int, c["depths"])), tuple(map(int, c["rehearsal_requests_per_pass"])), tuple(map(int, c["rehearsal_tiles_per_pass"])), int(c["repeats"]), False)


# --- seeds and hashes ----------------------------------------------------------------------------------------------------------------------------
def sha_seed(text: str) -> int:
    """Ruling 1: the first 8 bytes of SHA-256(text), big-endian, modulo 2**63."""
    return int.from_bytes(hashlib.sha256(text.encode()).digest()[:8], "big") % 2**63


def in_test_range(seed: int, cfg: Mapping[str, Any]) -> bool:
    lo, hi = cfg["seeds"]["test_range"]
    return int(lo) <= int(seed) <= int(hi)


# --- statistics (ruling 10) ----------------------------------------------------------------------------------------------------------------------
def nearest_rank(values: Sequence[float], q: float) -> float:
    """Nearest-rank percentile on the sorted values: the value at 1-indexed rank ceil(q n), at least 1."""
    if not values:
        raise ValueError("a percentile of nothing")
    ordered = sorted(values)
    rank = max(1, math.ceil(q * len(ordered) - 1e-12))
    return float(ordered[min(rank, len(ordered)) - 1])


def median(values: Sequence[float]) -> float:
    """The median by the nearest-rank rule (the value at rank ceil(n / 2))."""
    return nearest_rank(values, 0.5)


def cv(values: Sequence[float]) -> float | None:
    """Sample standard deviation (n - 1) over the mean; None for fewer than two values or a zero mean."""
    n = len(values)
    if n < 2:
        return None
    mean = math.fsum(values) / n
    if mean == 0:
        return None
    var = math.fsum((v - mean) ** 2 for v in values) / (n - 1)
    return math.sqrt(var) / mean


def margin_from_cv(cv_r: float, cfg: Mapping[str, Any]) -> tuple[float, bool]:
    """m_t = max(0.10, 2 x CV_R); the second value is True when m_t would exceed 0.30 (EQ-B's label is then ENGINEERING NOT EVALUABLE (TIMING SPREAD))."""
    t = cfg["thresholds"]
    m = max(float(t["m_floor"]), float(t["m_cv_multiple"]) * cv_r)
    return m, m > float(t["m_ceiling"])


# --- records -------------------------------------------------------------------------------------------------------------------------------------
def utc_stamp(now: datetime | None = None) -> str:
    return (now or datetime.now(UTC)).strftime("%Y%m%dT%H%M%S%fZ")


def envelope(kind: str) -> dict[str, Any]:
    if kind not in KINDS:
        raise ValueError(f"unknown record kind {kind!r}")
    return {"kind": kind, "schema": SCHEMA, "study": STUDY}


def check_envelope(record: Mapping[str, Any], kind: str | None = None) -> None:
    if record.get("study") != STUDY or record.get("schema") != SCHEMA or record.get("kind") not in KINDS:
        raise ValueError("P10IS5 record needs study, schema and a registered kind")
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


def append_jsonl(path: Path, obj: Mapping[str, Any]) -> None:
    """Append one JSON line atomically (one ``write`` on an ``O_APPEND`` descriptor, then ``fsync``): the readings of an attempt survive a kill."""
    import json
    import os

    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        os.write(fd, (json.dumps(jsonable(dict(obj)), sort_keys=True) + "\n").encode())
        os.fsync(fd)
    finally:
        os.close(fd)


def read_record(path: Path, kind: str | None = None) -> dict[str, Any]:
    rec = read_json(path)
    if not isinstance(rec, dict):
        raise ValueError(f"not a P10IS5 record: {path}")
    check_envelope(rec, kind)
    return rec


# --- keys (every distinguishing name is part of the key, so two records can never share one) ----------------------------------------------------------
def pass_key(stage: str, repeat: int, k: int, s: int, attempt: int = 1) -> str:
    if stage not in ("E2", "M", "K") or repeat < 1 or k < 1 or s < 1 or attempt < 1:
        raise ValueError(f"not a pass key: {(stage, repeat, k, s, attempt)!r}")
    return f"{stage}|r{repeat}|k{k}|s{s}|a{attempt}"


def parse_pass_key(key: str) -> tuple[str, int, int, int, int]:
    parts = key.split("|")
    if len(parts) != 5 or parts[1][0] != "r" or parts[2][0] != "k" or parts[3][0] != "s" or parts[4][0] != "a":
        raise ValueError(f"not a pass key: {key!r}")
    stage, r, k, s, a = parts[0], int(parts[1][1:]), int(parts[2][1:]), int(parts[3][1:]), int(parts[4][1:])
    pass_key(stage, r, k, s, a)
    return stage, r, k, s, a


def block_key(stage: str, repeat: int, attempt: int = 1) -> str:
    if stage not in ("E2", "M", "K") or repeat < 1 or attempt < 1:
        raise ValueError(f"not a block key: {(stage, repeat, attempt)!r}")
    return f"{stage}|r{repeat}|a{attempt}"


def safe_name(key: str) -> str:
    return key.replace("|", "_")


# --- charged-time ledger (hours) ----------------------------------------------------------------------------------------------------------------
class LedgerRefused(RuntimeError):
    """The charged-hours cap is spent: PAUSED, extendable only on projection by the human lead."""


class HoursLedger:
    """Charged wall time of the study, in ONE JSON file in the study's one run directory (never inside the frozen worktree). Every stage is charged (R0, R1, M, K, E1, P, E2 and its cold checks and harness figure);
    waiting for a quiet machine or for the cold wait is not charged (``slept`` is subtracted). The total cap and the per-group caps (rehearsal, e1, e2) are cumulative over stages and resumes."""

    def __init__(self, path: Path, total_seconds: float, group_caps: Mapping[str, float] | None = None) -> None:
        if not math.isfinite(total_seconds) or total_seconds <= 0:
            raise ValueError("the cap must be a positive number of seconds")
        self.path, self.total_seconds = path, float(total_seconds)
        self.group_caps = {k: float(v) for k, v in (group_caps or {}).items()}

    def entries(self) -> list[dict[str, Any]]:
        if not self.path.is_file():
            return []
        data = read_json(self.path)
        if not isinstance(data, dict) or data.get("study") != STUDY or data.get("kind") != "hours_ledger":
            raise ValueError(f"not a P10IS5 hours ledger: {self.path}")
        return list(data["entries"])

    def charged(self, group: str | None = None) -> float:
        return float(sum(float(e["seconds"]) for e in self.entries() if group is None or STAGE_GROUP.get(e["stage"], e["stage"]) == group))

    def require_room(self, stage: str = "E2", extra: float = 0.0) -> None:
        """PAUSED when the total or the stage group's cap is spent (``extra`` is the seconds of the stage's own run not yet written)."""
        if self.total_seconds - self.charged() - extra <= 0:
            raise LedgerRefused(f"the total cap of {self.total_seconds:.0f} s is spent; the stage is PAUSED and the extension is the human lead's")
        g = STAGE_GROUP.get(stage, stage)
        if g in self.group_caps and self.group_caps[g] - self.charged(g) - extra <= 0:
            raise LedgerRefused(f"the cap of group {g} ({self.group_caps[g]:.0f} s) is spent; the stage is PAUSED and the extension is the human lead's")

    def charge(self, stage: str, run: str, seconds: float) -> None:
        entries = self.entries()
        entries.append({"stage": stage, "run": run, "seconds": max(0.0, float(seconds)), "utc": datetime.now(UTC).isoformat()})
        self.path.parent.mkdir(parents=True, exist_ok=True)
        write_json(self.path, {**envelope("hours_ledger"), "total_seconds": self.total_seconds, "entries": entries})

    @contextlib.contextmanager
    def timed(self, stage: str, run: str, clock: Callable[[], float], slept: Callable[[], float]) -> Iterator[None]:
        """Charge the wall time of the block (the sleeping done inside it is not charged), also when it raises. Refuses to start when the cap is spent."""
        self.require_room(stage)
        t0, s0 = clock(), slept()
        try:
            yield
        finally:
            self.charge(stage, run, (clock() - t0) - (slept() - s0))


def hours_ledger_for(path: Path, cfg: Mapping[str, Any]) -> HoursLedger:
    c = cfg["caps"]
    return HoursLedger(path, float(c["total_hours"]) * 3600.0, {"rehearsal": float(c["rehearsal_hours"]) * 3600.0, "e1": float(c["e1_hours"]) * 3600.0, "e2": float(c["e2_hours"]) * 3600.0})
