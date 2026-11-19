# ruff: noqa: E501
"""P10IS6 shared contract (ADR-0031): config (every threshold lives in ``configs/p10i_s6_flat_lead_persistence.toml``), arms, rungs, cells, seeds, key scheme, record IO, pause file, ledger.

No torch is imported here. ``EngineeringStop`` and ``FailedCell`` are the P10-I-S3 classes re-exported (a frozen import, ADR-0031 section 15), because ``studies.p10i_s3.model.train_step`` raises that ``FailedCell``.
Nothing in this module reads a P10-I-S3 value. Self-check only: not independent review, not Astra validation, not human approval.
"""

import math
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from arborlm.io import file_sha256, read_json, write_json
from studies.p10i_s3.core import (  # frozen imports (section 15): classes and a pure function
    EngineeringStop,
    FailedCell,
    jsonable,
)

__all__ = ["EngineeringStop", "FailedCell", "jsonable"]

STUDY = "P10IS6"
FAMILY = "P10IS6_FLAT_LEAD_PERSISTENCE"
SCHEMA = 1
SPEC = "docs/decisions/ADR-0031-p10-i-s6-flat-lead-persistence.md"
CONFIG = Path("configs/p10i_s6_flat_lead_persistence.toml")
STUDY_DIR = Path("studies/p10i_s6")
FREEZE_DIR = STUDY_DIR / "freeze"
PLAN = FREEZE_DIR / "plan.json"
RATE_TABLE = FREEZE_DIR / "rate_table.json"
FREEZE_RECORD = FREEZE_DIR / "freeze_record.json"
DECISION_2_GLOB = "results/p10i-s6-freeze-*/DECISION_2.md"

FLAT, DENSE, BASE = "M-FLAT", "D-ADAPT", "BASE"
ARMS = (FLAT, DENSE)
RECORD_KINDS = ("train", "eval", "gate", "stage_manifest", "freeze_plan", "freeze_record", "analysis", "rehearsal_public", "ledger", "engineering_stop", "attempt", "stage_start", "d0", "parents")

READ_ENABLED, READ_REPLAY, READ_DISABLED = "enabled", "replay", "disabled"
READ_P_USED, READ_X_MEAN, READ_V_MEAN, READ_X_MEAN_DENSE = "P_used", "X_mean", "V_mean", "X_mean_dense"
TRIPLE = (READ_ENABLED, READ_REPLAY, READ_DISABLED)
FLAT_READS = (*TRIPLE, READ_P_USED, READ_X_MEAN, READ_V_MEAN)
DENSE_READS = (*TRIPLE, READ_X_MEAN_DENSE)
READS_OF = {FLAT: FLAT_READS, DENSE: DENSE_READS}
DRAWN = (READ_P_USED,)
# evaluation modes of one snapshot of a registered run (G2, G12): "step0" enabled+disabled; "enabled" the enabled read (the along-run curve and the delta-run points); "triple" enabled, replay, disabled (rung -1); "full" the whole read set of the arm
MODES = ("step0", "enabled", "triple", "full")


def read_list(arm: str, mode: str, draws: int = 4) -> list[tuple[str, int]]:
    if mode == "step0":
        return [(READ_ENABLED, 0), (READ_DISABLED, 0)]
    if mode == "enabled":
        return [(READ_ENABLED, 0)]
    if mode == "triple":
        return [(r, 0) for r in TRIPLE]
    if mode == "full":
        return [(r, d) for r in READS_OF[arm] for d in (range(draws) if r in DRAWN else [0])]
    raise ValueError(f"unknown mode {mode!r}")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


_REQUIRED: dict[str, tuple[str, ...]] = {
    "setting": ("backbone_parameters", "batch", "context", "positions_per_eval_batch", "panel_chunks", "val_targets", "slots", "dense_width", "adamw_betas", "adamw_eps", "weight_decay", "grad_clip", "chunk_bytes"),
    "ladder": ("base_updates", "rungs", "below_updates", "parent_updates", "min_rungs_after_cut"),
    "convergence": ("epsilon",),
    "rates": ("grid", "extension_up", "extension_down", "tie_tolerance", "max_extensions_up", "max_extensions_down"),
    "thresholds": ("effect", "min_cells", "min_parents", "cells", "parents", "calibration_cells", "half", "dense_share", "dense_floor", "dense_tolerance", "tolerance_neg_ref", "trend_delta"),
    "controls": ("p_used_draws", "min_used_slots"),
    "data": ("publisher_repo", "revision", "configuration", "rank_label", "wikitext2_rank_label", "calibration_article_mod", "calibration_article_residue", "fallback_article_mod", "fallback_article_residue", "pool_chunks_for_umax", "panel_walk_start", "download_expected_bytes", "download_hard_stop_bytes", "d0_rss_bytes", "chunk_table_name"),
    "seeds": ("stream_base", "oa_stream_base", "p_used_base", "order_registered", "order_calibration", "cal_stream_base", "cal_p_used_base", "dry_stream", "dry_p_used_base", "init_registered_base", "init_oa", "backbone_registered", "backbone_calibration", "init_calibration", "init_dry", "init_planted_toy", "held_dry_backbone", "held_dry_order", "held_dry_oa_stream", "init_test", "test_range", "control_memory_reuse"),
    "resources": ("workers", "rss_worker_bytes", "rss_aggregate_bytes", "rss_aggregate_alone_bytes", "snapshot_bytes_estimate"),
    "caps": ("provisional", "d0_p0_hours", "rehearsal_hours", "registered_hours_bound"),
    "seal": ("forbidden_roots", "expected_snapshot_gb"),
    "platform": ("system", "machine", "torch", "torch_num_threads", "torch_interop_threads", "deterministic_algorithms"),
    "seed_ranges": ("stream", "calibration", "init", "order", "test", "checker", "checker_sha256", "addendum", "addendum_sha256", "own_globs", "allocation_label"),
    "launch": ("keep_awake",),
    "gates": ("identity_rate", "identity_cell"),
}  # fmt: skip


def validate_config(data: Mapping[str, Any]) -> Mapping[str, Any]:
    if data.get("schema_version") != SCHEMA or data.get("experiment_family") != FAMILY or data.get("spec_reference") != SPEC:
        raise ValueError("P10IS6 config: schema_version, experiment_family or spec_reference differ")
    for section, keys in _REQUIRED.items():
        block = data.get(section)
        if not isinstance(block, dict):
            raise ValueError(f"P10IS6 config: section [{section}] is missing")
        missing = [k for k in keys if k not in block]
        if missing:
            raise ValueError(f"P10IS6 config: [{section}] lacks {missing}")

    def walk(v: Any) -> None:
        if isinstance(v, float) and not math.isfinite(v):
            raise ValueError("P10IS6 config: a non-finite number")
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
    """Provenance only: the ADR text is not a frozen input."""
    return file_sha256((root or repo_root()) / SPEC)


@dataclass(frozen=True)
class Thresholds:
    effect: float
    min_cells: int
    min_parents: int
    cells: int
    parents: int
    half: float
    dense_share: float
    dense_floor: float
    dense_tolerance: float
    tolerance_neg_ref: float
    trend_delta: float
    epsilon: float
    tie_tolerance: float

    @classmethod
    def from_config(cls, cfg: Mapping[str, Any]) -> "Thresholds":
        """Explicit argument only: this study never reads a configuration implicitly (F14)."""
        t = cfg["thresholds"]
        return cls(float(t["effect"]), int(t["min_cells"]), int(t["min_parents"]), int(t["cells"]), int(t["parents"]), float(t["half"]), float(t["dense_share"]), float(t["dense_floor"]), float(t["dense_tolerance"]), float(t["tolerance_neg_ref"]), float(t["trend_delta"]), float(cfg["convergence"]["epsilon"]), float(cfg["rates"]["tie_tolerance"]))  # fmt: skip

    def scaled(self, cells: int) -> "Thresholds":
        """Never used for a registered label: the same numbers over other denominators (tests and DRY rehearsals)."""
        from dataclasses import replace

        return replace(self, cells=cells, parents=cells // 3)


# --- the ladder (section 4) --------------------------------------------------------------------------------------------------------------
def rung_updates(cfg: Mapping[str, Any], k: int) -> int:
    """U_k = 16,384 * 2^k for k = 0..4 and U_{-1} = 8,192."""
    lad = cfg["ladder"]
    if k == -1:
        return int(lad["below_updates"])
    if not 0 <= k < int(lad["rungs"]):
        raise ValueError(f"rung {k} is outside the ladder")
    return int(lad["base_updates"]) * 2**k


def rung_range(k_max: int) -> list[int]:
    """-1..k_max"""
    return list(range(-1, k_max + 1))


def k_max_for_pools(cfg: Mapping[str, Any], registered_pool: int, calibration_pool: int) -> int:
    """Section 6.5, the ceiling rule (fixed by code from counts alone before any calibration run): the largest rung whose stream (8 chunks per update, no chunk used twice) both pools support; below rung 2: ENGINEERING STOP — CORPUS TOO SMALL."""
    lad = cfg["ladder"]
    best = -1
    for k in range(int(lad["rungs"])):
        need = 8 * rung_updates(cfg, k)
        if registered_pool >= need and calibration_pool >= need:
            best = k
    if best < int(lad["min_rungs_after_cut"]) - 1:
        raise EngineeringStop(f"ENGINEERING STOP — CORPUS TOO SMALL: the pools ({registered_pool}, {calibration_pool}) support rung {best}, below rung {int(lad['min_rungs_after_cut']) - 1}")
    return best


# --- cells and seeds (sections 7 and 14) ---------------------------------------------------------------------------------------------------
def parent_of(cell: int) -> int:
    return cell // 3


def seed_position(cell: int) -> int:
    return cell % 3


def old_parent_ids(parent: int) -> tuple[int, int]:
    """The nine old parents (OA): backbone 101 + p // 3, order 301 + p % 3."""
    return 101 + parent // 3, 301 + parent % 3


def parent_label(profile_group: str, parent: int) -> str:
    return f"{profile_group}{parent:02d}"


PROFILES = ("registered", "oa", "calibration", "dry", "test")
CELLS_OF = {"registered": 27, "oa": 27, "calibration": 3, "dry": 1, "test": 27}


class Seeds:
    """The seeds of one profile of cell ``c`` (section 14); draw j = 0..3. Every value comes from the config; no literal is in this code."""

    def __init__(self, profile: str, cfg: Mapping[str, Any]) -> None:
        if profile not in PROFILES:
            raise ValueError(profile)
        self.profile, self.s = profile, cfg["seeds"]

    def _check(self, c: int, j: int = 0) -> None:
        if not (0 <= c < CELLS_OF[self.profile] and 0 <= j < 4):
            raise ValueError("cell or draw out of range")

    def _t(self, k: int) -> int:
        return int(self.s["test_range"][0]) + k

    def stream(self, c: int) -> int:
        self._check(c)
        return {"registered": int(self.s["stream_base"]) + c, "oa": int(self.s["oa_stream_base"]) + c, "calibration": int(self.s["cal_stream_base"]) + c, "dry": int(self.s["dry_stream"]), "test": self._t(c)}[self.profile]

    def init(self, c: int) -> int:
        self._check(c)
        if self.profile == "registered":
            return int(self.s["init_registered_base"]) + c
        if self.profile == "oa":
            return int(self.s["init_oa"][c % 3])
        if self.profile == "calibration":
            return int(self.s["init_calibration"])
        if self.profile == "dry":
            return int(self.s["init_dry"])
        return int(self.s["init_test"][c % 2])

    def p_used(self, c: int, j: int) -> int:
        self._check(c, j)
        if self.profile == "oa":
            raise ValueError("the OA block has no P_used read")
        return {"registered": int(self.s["p_used_base"]) + 4 * c + j, "calibration": int(self.s["cal_p_used_base"]) + 4 * c + j, "dry": int(self.s["dry_p_used_base"]) + j, "test": self._t(300 + 4 * c + j)}[self.profile]


def order_seed(cfg: Mapping[str, Any], group: str, p: int) -> int:
    return int(cfg["seeds"]["order_registered" if group == "registered" else "order_calibration"][p])


def backbone_seed(cfg: Mapping[str, Any], group: str, p: int) -> int:
    return int(cfg["seeds"]["backbone_registered" if group == "registered" else "backbone_calibration"][p])


def test_seed(k: int, cfg: Mapping[str, Any]) -> int:
    lo, hi = cfg["seeds"]["test_range"]
    if not 0 <= k <= hi - lo:
        raise ValueError("test seed out of range")
    return int(lo) + k


# --- keys (every distinguishing name) ----------------------------------------------------------------------------------------------------------
def rate_label(rate: float) -> str:
    return f"{rate:.6g}"


def run_key(arm: str, rate: float, cell: int, *, oa: bool = False) -> str:
    if arm not in ARMS:
        raise ValueError("unknown arm")
    return f"run{'oa' if oa else ''}|{arm}|r{rate_label(rate)}|c{cell:02d}"


def nll_key(arm: str, rate: float, cell: int, update: int, read: str, draw: int = 0, *, oa: bool = False) -> str:
    """Arm, rate, cell, update, read and draw are all in the key (a rung's records can never share a key)."""
    if arm not in ARMS or read not in READS_OF[arm]:
        raise ValueError(f"not a read of {arm}: {read}")
    return f"nll{'oa' if oa else ''}|{arm}|r{rate_label(rate)}|c{cell:02d}|u{update:06d}|{read}|d{draw}"


def base_key(parent: int, read: str = READ_ENABLED, *, oa: bool = False) -> str:
    return f"base{'oa' if oa else ''}|p{parent:02d}|{read}"


def stat_key(arm: str, rate: float, cell: int, update: int, name: str) -> str:
    return f"stat|{arm}|r{rate_label(rate)}|c{cell:02d}|u{update:06d}|{name}"


# --- records ---------------------------------------------------------------------------------------------------------------------------------
def envelope(kind: str) -> dict[str, Any]:
    if kind not in RECORD_KINDS:
        raise ValueError(f"unknown record kind {kind!r}")
    return {"kind": kind, "schema": SCHEMA, "study": STUDY}


def check_envelope(record: Mapping[str, Any], kind: str | None = None) -> None:
    if record.get("study") != STUDY or record.get("schema") != SCHEMA or record.get("kind") not in RECORD_KINDS:
        raise ValueError("P10IS6 record needs study, schema and a registered kind")
    if kind is not None and record.get("kind") != kind:
        raise ValueError(f"expected a {kind!r} record, got {record.get('kind')!r}")


def write_record(path: Path, record: Mapping[str, Any], *, overwrite: bool = False) -> None:
    check_envelope(record)
    if path.exists() and not overwrite:
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, jsonable(dict(record)))


def read_record(path: Path, kind: str | None = None) -> dict[str, Any]:
    rec = read_json(path)
    if not isinstance(rec, dict):
        raise ValueError(f"not a P10IS6 record: {path}")
    check_envelope(rec, kind)
    return rec


def log_attempt(run_dir: Path, what: str, **fields: Any) -> Path:
    """Requirement 4: every attempt, pause and failure is written to the run directory as it happens and is never overwritten (one file per event)."""
    d = run_dir / "attempts"
    d.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    n = len(list(d.glob(f"{stamp}-*.json")))
    path = d / f"{stamp}-{n:02d}-{what.replace(' ', '_').replace('/', '~')[:60]}.json"
    write_record(path, {**envelope("attempt"), "what": what, "utc": datetime.now(UTC).isoformat(), **fields})
    return path


# --- the lead's pause file (F19): a file in the RUN directory --------------------------------------------------------------------------------
PAUSE_FILE = "pause-request"


def pause_requested(run_dir: Path) -> str | None:
    """Workers check this at item boundaries (before starting an item, and at a rung snapshot of a long run). Anyone creates ``<run>/pause-request`` (its text is the reason) and removes it to resume."""
    p = run_dir / PAUSE_FILE
    if not p.is_file():
        return None
    return p.read_text(encoding="utf-8", errors="replace").strip() or "no reason given"


# --- the ledger of charged time -----------------------------------------------------------------------------------------------------------------
class Ledger:
    """Charged wall seconds of every stage invocation (R2's, R3's and the registered stages' share one), in the public run directory, never inside a working tree. An invocation gets the cap minus what is charged."""

    def __init__(self, path: Path, total_seconds: float) -> None:
        if not math.isfinite(total_seconds) or total_seconds <= 0:
            raise ValueError("the cap must be a positive number of seconds")
        self.path, self.total_seconds = path, float(total_seconds)

    def entries(self) -> list[dict[str, Any]]:
        if not self.path.is_file():
            return []
        data = read_json(self.path)
        if not isinstance(data, dict) or data.get("study") != STUDY or data.get("kind") != "ledger":
            raise ValueError(f"not a P10IS6 ledger: {self.path}")
        return list(data["entries"])

    def charged(self) -> float:
        return float(sum(float(e["seconds"]) for e in self.entries()))

    def remaining(self) -> float:
        return max(0.0, self.total_seconds - self.charged())

    def charge(self, stage: str, seconds: float) -> None:
        entries = self.entries()
        entries.append({"stage": stage, "seconds": max(0.0, float(seconds)), "utc": datetime.now(UTC).isoformat()})
        self.path.parent.mkdir(parents=True, exist_ok=True)
        write_json(self.path, {"study": STUDY, "kind": "ledger", "schema": SCHEMA, "total_seconds": self.total_seconds, "entries": entries})
