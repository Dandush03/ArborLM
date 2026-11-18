# ruff: noqa: E501
"""P10IS3 shared contract (ADR-0026): config (every threshold lives in ``configs/p10i_s3_longer_training.toml``), arms, regimes, cell indices, seeds, key scheme, record IO, pause file.

No torch is imported here. Self-check only: not independent review, not Astra validation, not human approval.
"""

import math
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from arborlm.io import file_sha256, read_json, write_json

STUDY = "P10IS3"
FAMILY = "P10IS3_LONGER_TRAINING"
SCHEMA = 1
SPEC = "docs/decisions/ADR-0026-p10-i-s3-longer-training.md"
CONFIG = Path("configs/p10i_s3_longer_training.toml")
FREEZE_DIR = Path("studies/p10i_s3/freeze")
PLAN = FREEZE_DIR / "plan.json"
RATE_TABLE = FREEZE_DIR / "rate_table.json"
FREEZE_RECORD = FREEZE_DIR / "freeze_record.json"

TREE, FLAT, DENSE, BASE = "M-TREE", "M-FLAT", "D-ADAPT", "BASE"
ARMS = (TREE, FLAT, DENSE)
REP, REPU, FRESH = "REP", "REP-U", "FRESH"
REGIMES = (REP, REPU, FRESH)
REGIME_ARMS = {REP: (TREE, FLAT, DENSE), REPU: (TREE, DENSE), FRESH: (TREE, FLAT, DENSE)}
REGIME_INDEX = {REP: 0, REPU: 1, FRESH: 2}
RECORD_KINDS = ("train", "eval", "gate", "stage_manifest", "freeze_plan", "freeze_record", "analysis", "rehearsal_public", "ledger", "engineering_stop")

# reads (evaluation names)
READ_ENABLED, READ_REPLAY, READ_DISABLED = "enabled", "replay", "disabled"
READ_P_ALL, READ_P_USED, READ_X, READ_X_MEAN = "P_all", "P_used", "X", "X_mean"
READ_JOINT, READ_EXHAUSTIVE, READ_PRIOR_OFF = "joint", "exhaustive", "prior_off"
READ_X_DENSE, READ_X_MEAN_DENSE = "X_dense", "X_mean_dense"
DRAWN_READS = (READ_P_USED, READ_X, READ_X_DENSE)

TREE_READS = (READ_ENABLED, READ_REPLAY, READ_DISABLED, READ_P_ALL, READ_P_USED, READ_X_MEAN, READ_X, READ_JOINT, READ_EXHAUSTIVE, READ_PRIOR_OFF)
FLAT_READS = (READ_ENABLED, READ_REPLAY, READ_DISABLED, READ_P_ALL, READ_P_USED, READ_X_MEAN, READ_X)
DENSE_READS = (READ_ENABLED, READ_REPLAY, READ_DISABLED, READ_X_DENSE, READ_X_MEAN_DENSE)
READS_OF = {TREE: TREE_READS, FLAT: FLAT_READS, DENSE: DENSE_READS}


def read_list(arm: str, draws: int = 4) -> list[tuple[str, int]]:
    """(read, draw) pairs of one checkpoint of ``arm``: 16 for M-TREE, 13 for M-FLAT, 8 for D-ADAPT (section 9)."""
    return [(r, d) for r in READS_OF[arm] for d in (range(draws) if r in DRAWN_READS else [0])]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


_REQUIRED: dict[str, tuple[str, ...]] = {
    "setting": ("backbones", "orders", "batch", "context", "positions_per_eval_batch", "panel_chunks", "val_targets", "slots", "dense_width", "adamw_betas", "adamw_eps", "weight_decay", "grad_clip"),
    "duration": ("u_star", "checkpoints", "step_zero", "epsilon", "past_best_margin"),
    "rates": ("grid", "extension_up", "extension_down", "tie_tolerance", "max_extensions_per_side", "p4_rate"),
    "thresholds": ("effect", "dense_tolerance", "min_cells", "min_parents", "cells", "parents", "calibration_cells", "half", "dense_share", "dense_floor", "tolerance_joint", "tolerance_neg_ref", "routing_effect", "loaded_load_average"),
    "controls": ("p_used_draws", "x_draws", "exhaustive_visit", "prior_off_visit"),
    "data": ("rep_ranks", "rep_u_ranks", "fresh_start", "eligible_train", "eligible_validation", "panel_walk_start", "fresh_pool", "max_fresh_updates"),
    "seeds": ("init_registered", "init_calibration", "init_dry", "init_test", "stream_base", "p_all_base", "joint_base", "p_used_base", "x_base", "cal_stream_base", "cal_p_all_base", "cal_joint_base", "cal_p_used_base", "cal_x_base", "dry_stream_base", "dry_p_all", "dry_joint", "dry_p_used_base", "dry_x_base", "test_range"),
    "resources": ("workers", "rss_worker_bytes", "rss_aggregate_bytes", "rss_aggregate_alone_bytes", "snapshot_bytes_estimate"),
    "caps": ("provisional", "rehearsal_hours", "registered_hours"),
    "platform": ("system", "machine", "torch", "torch_num_threads", "torch_interop_threads", "deterministic_algorithms"),
    "seed_ranges": ("stream", "calibration", "dry", "init", "test", "checker", "checker_sha256"),
}  # fmt: skip


def validate_config(data: Mapping[str, Any]) -> Mapping[str, Any]:
    if data.get("schema_version") != SCHEMA or data.get("experiment_family") != FAMILY or data.get("spec_reference") != SPEC:
        raise ValueError("P10IS3 config: schema_version, experiment_family or spec_reference differ")
    for section, keys in _REQUIRED.items():
        block = data.get(section)
        if not isinstance(block, dict):
            raise ValueError(f"P10IS3 config: section [{section}] is missing")
        missing = [k for k in keys if k not in block]
        if missing:
            raise ValueError(f"P10IS3 config: [{section}] lacks {missing}")

    def walk(v: Any) -> None:
        if isinstance(v, float) and not math.isfinite(v):
            raise ValueError("P10IS3 config: a non-finite number")
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
    dense_tolerance: float
    min_cells: int
    min_parents: int
    cells: int
    parents: int
    half: float
    dense_share: float
    dense_floor: float
    tolerance_joint: float
    tolerance_neg_ref: float
    routing_effect: float
    epsilon: float
    past_best_margin: float
    tie_tolerance: float

    @classmethod
    def from_config(cls, cfg: Mapping[str, Any] | None = None) -> "Thresholds":
        c = cfg or load_config()
        t = c["thresholds"]
        return cls(float(t["effect"]), float(t["dense_tolerance"]), int(t["min_cells"]), int(t["min_parents"]), int(t["cells"]), int(t["parents"]), float(t["half"]), float(t["dense_share"]), float(t["dense_floor"]), float(t["tolerance_joint"]), float(t["tolerance_neg_ref"]), float(t["routing_effect"]), float(c["duration"]["epsilon"]), float(c["duration"]["past_best_margin"]), float(c["rates"]["tie_tolerance"]))  # fmt: skip

    def scaled(self, cells: int) -> "Thresholds":
        """Never used for a registered label: same numbers, other denominators (tests)."""
        from dataclasses import replace

        return replace(self, cells=cells, parents=cells // 3)


# --- cells and seeds (section 4) -------------------------------------------------------------------------------------
def cell_index(backbone: int, order: int, seed_position: int) -> int:
    return 9 * (backbone - 101) + 3 * (order - 301) + seed_position


def parent_of(cell: int) -> int:
    return cell // 3


def parent_label(parent: int) -> str:
    return f"b{101 + parent // 3}-o{301 + parent % 3}"


def parent_ids(parent: int) -> tuple[int, int]:
    return 101 + parent // 3, 301 + parent % 3


def seed_position(cell: int) -> int:
    return cell % 3


CAL_PARENTS = (0, 4, 8)  # B101/O301, B102/O302, B103/O303 (calibration cells c = 0..2 sit on these parents; section 5)


def calibration_parent(c: int) -> int:
    return CAL_PARENTS[c]


class Seeds:
    """The seeds of one profile (registered, calibration, dry, test) of cell ``c`` and regime ``g``; draw j = 0..3. Values copied from the registry through the config."""

    def __init__(self, profile: str, cfg: Mapping[str, Any] | None = None) -> None:
        if profile not in ("registered", "calibration", "dry", "test"):
            raise ValueError(profile)
        self.profile, self.s = profile, (cfg or load_config())["seeds"]

    def init(self, c: int) -> int:
        if self.profile == "registered":
            return int(self.s["init_registered"][c % 3])
        if self.profile == "calibration":
            return int(self.s["init_calibration"])
        if self.profile == "dry":
            return int(self.s["init_dry"])
        return int(self.s["init_test"][c % 2])

    def _check(self, c: int, g: int, j: int = 0) -> None:
        n = {"registered": 27, "calibration": 3, "dry": 1, "test": 27}[self.profile]
        if not (0 <= c < n and 0 <= g < 3 and 0 <= j < 4):
            raise ValueError("cell, regime or draw out of range")

    def _t(self, k: int) -> int:
        return int(self.s["test_range"][0]) + k

    def stream(self, c: int, g: int) -> int:
        self._check(c, g)
        if self.profile == "test":
            return self._t(3 * c + g)
        if self.profile == "registered":
            return int(self.s["stream_base"]) + 3 * c + g
        if self.profile == "calibration":
            return int(self.s["cal_stream_base"]) + 3 * c + g
        return int(self.s["dry_stream_base"]) + g

    def p_all(self, c: int) -> int:
        self._check(c, 0)
        return {"registered": int(self.s["p_all_base"]) + c, "calibration": int(self.s["cal_p_all_base"]) + c, "test": self._t(100 + c)}.get(self.profile, int(self.s["dry_p_all"]))

    def joint(self, c: int) -> int:
        self._check(c, 0)
        return {"registered": int(self.s["joint_base"]) + c, "calibration": int(self.s["cal_joint_base"]) + c, "test": self._t(200 + c)}.get(self.profile, int(self.s["dry_joint"]))

    def p_used(self, c: int, j: int) -> int:
        self._check(c, 0, j)
        return {"registered": int(self.s["p_used_base"]) + 4 * c + j, "calibration": int(self.s["cal_p_used_base"]) + 4 * c + j, "test": self._t(300 + 4 * c + j)}.get(self.profile, int(self.s["dry_p_used_base"]) + j)

    def x(self, c: int, j: int) -> int:
        self._check(c, 0, j)
        return {"registered": int(self.s["x_base"]) + 4 * c + j, "calibration": int(self.s["cal_x_base"]) + 4 * c + j, "test": self._t(500 + 4 * c + j)}.get(self.profile, int(self.s["dry_x_base"]) + j)


def test_seed(k: int, cfg: Mapping[str, Any] | None = None) -> int:
    lo, hi = (cfg or load_config())["seeds"]["test_range"]
    if not 0 <= k <= hi - lo:
        raise ValueError("test seed out of range")
    return int(lo) + k


# --- keys ---------------------------------------------------------------------------------------------------------------
def rate_label(rate: float) -> str:
    return f"{rate:.6g}"


def run_key(arm: str, regime: str, rate: float, cell: int) -> str:
    if arm not in ARMS or regime not in REGIMES:
        raise ValueError("unknown arm or regime")
    return f"run|{arm}|{regime}|r{rate_label(rate)}|c{cell:02d}"


def nll_key(arm: str, regime: str, rate: float, cell: int, ckpt: int, read: str, draw: int = 0) -> str:
    """Every distinguishing name is in the key: arm, regime, rate, cell, checkpoint, read and draw (ruling 16)."""
    if arm not in ARMS or regime not in REGIMES or read not in READS_OF[arm]:
        raise ValueError(f"not a read of {arm}: {read}")
    return f"nll|{arm}|{regime}|r{rate_label(rate)}|c{cell:02d}|u{ckpt:05d}|{read}|d{draw}"


def base_key(parent: int, read: str = "enabled") -> str:
    return f"base|{parent_label(parent)}|{read}"


def stat_key(arm: str, regime: str, rate: float, cell: int, ckpt: int, name: str) -> str:
    return f"stat|{arm}|{regime}|r{rate_label(rate)}|c{cell:02d}|u{ckpt:05d}|{name}"


# --- records ---------------------------------------------------------------------------------------------------------------
def envelope(kind: str) -> dict[str, Any]:
    if kind not in RECORD_KINDS:
        raise ValueError(f"unknown record kind {kind!r}")
    return {"kind": kind, "schema": SCHEMA, "study": STUDY}


def check_envelope(record: Mapping[str, Any], kind: str | None = None) -> None:
    if record.get("study") != STUDY or record.get("schema") != SCHEMA or record.get("kind") not in RECORD_KINDS:
        raise ValueError("P10IS3 record needs study, schema and a registered kind")
    if kind is not None and record.get("kind") != kind:
        raise ValueError(f"expected a {kind!r} record, got {record.get('kind')!r}")


def jsonable(v: Any) -> Any:
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
        raise ValueError(f"not a P10IS3 record: {path}")
    check_envelope(rec, kind)
    return rec


# --- the lead's pause file (K6): a file in the RUN directory, never inside the frozen set ------------------------------------
PAUSE_FILE = "PAUSE_BY_LEAD"


def pause_requested(run_dir: Path) -> str | None:
    """Workers check this between tasks. The lead creates ``<run>/PAUSE_BY_LEAD`` (its text is the reason) and removes it to resume; the stage manifest then says PAUSED — BY THE LEAD."""
    p = run_dir / PAUSE_FILE
    return p.read_text(encoding="utf-8", errors="replace").strip() or "no reason given" if p.is_file() else None


class EngineeringStop(RuntimeError):
    """A defect of code, plan, environment or a non-finite value outside the scientific rules: nothing is labelled (section 10)."""


class FailedCell(ValueError):
    """A non-finite event as section 6.1 defines it (training loss, clipped gradient norm, trainable parameter, or enabled NLL at the registered checkpoint). Applies to calibration and DRY runs too (K1)."""


# --- the ledger of charged time (R1: caps are cumulative across stages and resumes) ----------------------------------------------------------
class Ledger:
    """Charged wall seconds of every stage invocation of one run (the rehearsal's R1 rounds, R2 and R3 share one; so do the registered stages), appended to one JSON file in the public run directory (never inside a
    working tree where it would dirty it: ``plan.require_ignored_path``). An invocation gets the cap minus what is charged; nothing left means PAUSED."""

    def __init__(self, path: Path, total_seconds: float) -> None:
        if not math.isfinite(total_seconds) or total_seconds <= 0:
            raise ValueError("the cap must be a positive number of seconds")
        self.path, self.total_seconds = path, float(total_seconds)

    def entries(self) -> list[dict[str, Any]]:
        if not self.path.is_file():
            return []
        data = read_json(self.path)
        if not isinstance(data, dict) or data.get("study") != STUDY or data.get("kind") != "ledger":
            raise ValueError(f"not a P10IS3 ledger: {self.path}")
        return list(data["entries"])

    def charged(self) -> float:
        return float(sum(float(e["seconds"]) for e in self.entries()))

    def remaining(self) -> float:
        return max(0.0, self.total_seconds - self.charged())

    def charge(self, stage: str, seconds: float) -> None:
        from datetime import UTC, datetime

        entries = self.entries()
        entries.append({"stage": stage, "seconds": max(0.0, float(seconds)), "utc": datetime.now(UTC).isoformat()})
        self.path.parent.mkdir(parents=True, exist_ok=True)
        write_json(self.path, {"study": STUDY, "kind": "ledger", "schema": SCHEMA, "total_seconds": self.total_seconds, "entries": entries})
