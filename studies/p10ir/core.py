# ruff: noqa: E501
"""P10IR shared contract (ADR-0029): the config, the thresholds (read from ``configs/p10ir_routing.toml`` and nowhere else), the cells, the checkpoints, the read names and the key scheme,
record kinds and record IO, seeds, the charged-time ledger. No torch is imported here except through the functions that name a P10-S1 object (``floor_i_bits``, ``s1_label``,
``bridge_label``, the seed sets), which import it on call; the label and analysis modules stay free of torch.

Every threshold is read from the config. The ADR text is not a frozen input: ``spec_sha256`` is for provenance only.
"""

import math
import re
import tomllib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NamedTuple

from arborlm.io import file_sha256, read_json, write_json

STUDY = "P10IR"
FAMILY = "P10IR_ROUTING_DIAGNOSIS"
SCHEMA = 1
SPEC = "docs/decisions/ADR-0029-p10-i-r-routing-diagnosis.md"
CONFIG = Path("configs/p10ir_routing.toml")
FREEZE_DIR = Path("studies/p10ir/freeze")
PLAN = FREEZE_DIR / "plan.json"
LAUNCH_DIR = Path("studies/p10ir/launch")
P10S1_PLAN = Path("studies/p10s1/freeze/plan.json")

STAGE_A1, STAGE_A2 = "A1", "A2"
STAGES = (STAGE_A1, STAGE_A2)
A1_TAG = "REGISTERED RE-ANALYSIS OF OBSERVED CELLS"
A2_TAG = "FRESH CHECKPOINTS"
STANDING_TAG = "ORACLE-ADDRESSED; RECALL OF TRAINED RANDOM FACTS; DICT DOMINATES ON THIS TASK"
STAGE_TAG = {STAGE_A1: A1_TAG, STAGE_A2: A2_TAG}
LIMIT_SENTENCE = (
    "A limit printed with every label: these are read-time changes to memories trained under the registered read. The tree's values and output projection were trained with the prior in the "
    "weights and two branches visited. A read-time change that does not help does not show that training without it would not; one that helps shows only that the trained content tolerates it. "
    "Causes that act during training need Stage B."
)

RECORD_KINDS = (
    "read", "item", "gate", "stage_manifest", "freeze_plan", "analysis", "ledger", "rehearsal", "bridge_manifest", "bridge_train", "identity_gate", "extract", "gates_record", "report_manifest", "confirm", "engineering_stop",
)  # fmt: skip

# --- the reads (section 6) and their names -----------------------------------------------------------------------------------------
TREE_NAMED = ("T0", "T1", "T1w", "T3", "T2")
FLAT_NAMED = ("F0", "I256@512")
PRIOR_STATES = ("on", "off")
TREE, FLAT = "tree", "flat"


def tv_name(v: int, prior: str) -> str:
    if prior not in PRIOR_STATES or v < 1:
        raise ValueError(f"not a visit-sweep read: v={v!r} prior={prior!r}")
    return f"Tv{v}_{prior}"


def i64_name(c: int, seed: int) -> str:
    """``I64@256/s298001``: the budget and the index seed are part of the read's name (the key of one read)."""
    if c < 1 or seed < 0:
        raise ValueError("an I64 read needs a budget and an index seed")
    return f"I64@{c}/s{seed}"


_READ_RE = re.compile(r"^(T0|T1|T1w|T3|T2|F0|I256@512|Tv[1-9][0-9]*_(on|off)|I64@[1-9][0-9]*/s[0-9]+)$")


def is_read_name(name: str) -> bool:
    return bool(_READ_RE.match(name))


def read_key(stage: str, cell_label: str, update: int, read: str) -> str:
    """The registry key of one read of one checkpoint. The read's name is part of it, so two reads of one cell can never share a key (the defect of ``studies/p10s1/analysis.py`` lines 167-169)."""
    if stage not in STAGES or not cell_label or update < 1 or not is_read_name(read):
        raise ValueError(f"not a read key: {(stage, cell_label, update, read)!r}")
    return f"{stage}|{cell_label}|u{update:07d}|{read}"


def parse_read_key(key: str) -> tuple[str, str, int, str]:
    parts = key.split("|")
    if len(parts) != 4 or not parts[2].startswith("u"):
        raise ValueError(f"not a read key: {key!r}")
    stage, label, upd, read = parts
    read_key(stage, label, int(upd[1:]), read)  # validates
    return stage, label, int(upd[1:]), read


def item_id(stage: str, cell_label: str, update: int) -> str:
    """One item of a plan: one checkpoint of one cell (its reads are the item's list)."""
    if stage not in STAGES or not cell_label or update < 1:
        raise ValueError("not an item")
    return f"{stage}|{cell_label}|u{update:07d}"


# --- the config -------------------------------------------------------------------------------------------------------------------
def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


_REQUIRED: dict[str, tuple[str, ...]] = {
    "thresholds": ("gap_bits", "restored_margin_bits", "restored_ratio", "floor_a_use", "floor_i_bits_printed", "h_margin_bits", "closure", "recall_r", "plateau_gain_bits", "still_learning_min_replicates", "tree_candidates", "replicates", "label_min_replicates", "not_evaluable_min_replicates"),
    "gates": ("tie_margin", "weight_tolerance", "tie_share_max"),
    "reads": ("visit_sweep", "index_budgets", "index_list_size", "index_standard_budget", "index_standard_list_size", "lloyd_iterations", "branch_size", "visit_registered", "top", "temperature", "shallow_slots"),
    "seeds": ("bridge_base", "bridge_stride", "bridge_draws", "bridge_index_offset", "bridge_init_base", "index_seeds", "test_index_seeds", "rehearsal_base", "rehearsal_init", "test_init", "test_range", "p10s1_draw_base", "p10s1_draw_stride", "p10s1_index_offset", "p10s1_init_base", "identity_gate_draw", "identity_gate_updates", "identity_gate_cell"),
    "a2": ("learning_rate", "arms", "cells"),
    "resources": ("workers", "rss_worker_bytes", "rss_aggregate_bytes", "eval_chunk_elements"),
    "caps": ("provisional", "rehearsal_hours", "a1_hours", "a2_hours", "total_hours"),
    "platform": ("system", "machine", "torch", "torch_num_threads", "torch_interop_threads", "deterministic_algorithms"),
    "seed_ranges": ("bridge", "index", "rehearsal", "init", "test", "checker", "checker_sha256"),
    "rehearsal": ("facts", "slots", "updates", "snapshots", "synthetic_facts", "synthetic_slots", "synthetic_updates", "synthetic_snapshots"),
}  # fmt: skip


def validate_config(data: Mapping[str, Any]) -> Mapping[str, Any]:
    """Every section and key must exist; numbers must be finite; the cells must be the seven of section 4. Values are not compared to constants here: the config is the one place they live."""
    if data.get("schema_version") != SCHEMA or data.get("experiment_family") != FAMILY or data.get("spec_reference") != SPEC:
        raise ValueError("P10IR config: schema_version, experiment_family or spec_reference differ")
    for section, keys in _REQUIRED.items():
        block = data.get(section)
        if not isinstance(block, dict):
            raise ValueError(f"P10IR config: section [{section}] is missing")
        missing = [k for k in keys if k not in block]
        if missing:
            raise ValueError(f"P10IR config: [{section}] lacks {missing}")
    cells = data.get("cells")
    if not isinstance(cells, list) or len(cells) != 7:
        raise ValueError("P10IR config: [[cells]] must list the seven cells of stage A1")
    for c in cells:
        if set(c) != {"facts", "slots", "role", "u_p", "run", "trajectory"} or c["role"] not in ("primary", "printed", "loaded"):
            raise ValueError(f"P10IR config: bad cell entry {c!r}")
        if len(c["trajectory"]) != 2:
            raise ValueError("P10IR config: two trajectory checkpoints per cell")

    def walk(v: Any) -> None:
        if isinstance(v, float) and not math.isfinite(v):
            raise ValueError("P10IR config: a non-finite number")
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
    """Provenance only: the ADR text is not in the frozen-input set (section 13)."""
    return file_sha256((root or repo_root()) / SPEC)


@dataclass(frozen=True)
class Thresholds:
    """Every scientific threshold of the labels, from the config (section 12 'Scientific threshold')."""

    gap_bits: float
    restored_margin_bits: float
    restored_ratio: float
    floor_i_bits: float
    h_margin_bits: float
    closure: float
    recall_r: float
    plateau_gain_bits: float
    still_learning_min_replicates: int
    tree_candidates: int
    replicates: int
    label_min_replicates: int
    not_evaluable_min_replicates: int
    tie_margin: float
    weight_tolerance: float
    tie_share_max: float

    @classmethod
    def from_config(cls, cfg: Mapping[str, Any] | None = None) -> "Thresholds":
        c = cfg or load_config()
        t, g = c["thresholds"], c["gates"]
        return cls(
            float(t["gap_bits"]), float(t["restored_margin_bits"]), float(t["restored_ratio"]), floor_i_bits(float(t["floor_a_use"])), float(t["h_margin_bits"]), float(t["closure"]), float(t["recall_r"]),
            float(t["plateau_gain_bits"]), int(t["still_learning_min_replicates"]), int(t["tree_candidates"]), int(t["replicates"]), int(t["label_min_replicates"]), int(t["not_evaluable_min_replicates"]),
            float(g["tie_margin"]), float(g["weight_tolerance"]), float(g["tie_share_max"]),
        )  # fmt: skip


def floor_i_bits(a_use: float) -> float:
    """i at ``a_use`` by P10-S1's own function (``studies.p9.core.fano_bits_per_fact``, as ``studies.p10s1.core.PLATEAU_FLOOR_I`` is derived): 0.473 bits at a_use 0.25."""
    from studies.p9 import core as p9core

    return float(p9core.fano_bits_per_fact(a_use))


# --- cells and checkpoints (section 4) ------------------------------------------------------------------------------------------
def size_name(n: int) -> str:
    return f"{n // 1024}K" if n % 1024 == 0 else str(n)


def cell_name(facts: int, slots: int) -> str:
    """``8K/4K``: 8,192 facts in 4,096 slots."""
    return f"{size_name(facts)}/{size_name(slots)}"


class CellSpec(NamedTuple):
    facts: int
    slots: int
    role: str
    u_p: int
    run: int
    trajectory: tuple[int, int]

    @property
    def name(self) -> str:
        return cell_name(self.facts, self.slots)

    @property
    def branches(self) -> int:
        return self.slots // 256

    @property
    def run_half(self) -> int:
        return self.run // 2

    @property
    def shallow(self) -> bool:
        return self.slots == 1024

    def checkpoints(self) -> tuple[int, int, int, int]:
        """U_P, the run length and the two trajectory points, in ascending order."""
        return tuple(sorted({self.u_p, self.run, *self.trajectory}))  # type: ignore[return-value]

    @property
    def co_primary(self) -> tuple[int, int]:
        return self.u_p, self.run


def cell_specs(cfg: Mapping[str, Any] | None = None) -> list[CellSpec]:
    c = cfg or load_config()
    return [CellSpec(int(x["facts"]), int(x["slots"]), x["role"], int(x["u_p"]), int(x["run"]), (int(x["trajectory"][0]), int(x["trajectory"][1]))) for x in c["cells"]]


def primary_cells(cfg: Mapping[str, Any] | None = None) -> list[CellSpec]:
    return [c for c in cell_specs(cfg) if c.role == "primary"]


def spec_of(facts: int, slots: int, cfg: Mapping[str, Any] | None = None) -> CellSpec:
    for c in cell_specs(cfg):
        if (c.facts, c.slots) == (facts, slots):
            return c
    raise ValueError(f"{cell_name(facts, slots)} is not a cell of stage A1")


# --- feasibility (section 6): NOT APPLICABLE is a plan item, never silently skipped ---------------------------------------------
def feasible_visits(slots: int, cfg: Mapping[str, Any] | None = None) -> list[int]:
    """v in the sweep with v <= N/256."""
    c = cfg or load_config()
    return [int(v) for v in c["reads"]["visit_sweep"] if int(v) <= slots // int(c["reads"]["branch_size"])]


def feasible_budgets(slots: int, cfg: Mapping[str, Any] | None = None) -> list[int]:
    """c in the budgets with c < N."""
    c = cfg or load_config()
    return [int(b) for b in c["reads"]["index_budgets"] if int(b) < slots]


# --- labels of cells (P10-S1's own, imported on call) ------------------------------------------------------------------------------
def s1_label(arm: str, facts: int, slots: int, draw: int, u_p: int, run: int, cfg: Mapping[str, Any] | None = None) -> str:
    """The label of P10-S1's registered cell of ``arm`` (P10-S1's ``make_cell``; initialisation 2100 + draw)."""
    from studies.p10s1 import core as s1

    c = cfg or load_config()
    return s1.make_cell("P", arm, facts, slots, draw, int(c["seeds"]["p10s1_init_base"]) + draw, u_p=u_p, run_updates=run).label


def bridge_init_seed(draw: int, cfg: Mapping[str, Any] | None = None) -> int:
    c = cfg or load_config()
    if not 1 <= draw <= int(c["seeds"]["bridge_draws"]):
        raise ValueError("bridge draws are 1..5")
    return int(c["seeds"]["bridge_init_base"]) + draw


def bridge_label(arm: str, facts: int, slots: int, draw: int, u_p: int, run: int, cfg: Mapping[str, Any] | None = None) -> str:
    """The label of a bridge cell: P10-S1's label format with the bridge initialisation seed (so no bridge label equals a P10-S1 label)."""
    from studies.p10s1 import core as s1

    return s1.make_cell("P", arm, facts, slots, draw, bridge_init_seed(draw, cfg), u_p=u_p, run_updates=run).label


# --- seeds (section 5) -----------------------------------------------------------------------------------------------------------
def bridge_base(draw: int, cfg: Mapping[str, Any] | None = None) -> int:
    c = cfg or load_config()
    s = c["seeds"]
    if not 1 <= draw <= int(s["bridge_draws"]):
        raise ValueError("bridge draws are 1..5")
    return int(s["bridge_base"]) + int(s["bridge_stride"]) * (draw - 1)


def bridge_seeds(draw: int, cfg: Mapping[str, Any] | None = None) -> Any:
    """P10-S1's in-set layout (``studies.p10s1.core.seed_set``) on the bridge base of ``draw`` (index seed at base + 60)."""
    from studies.p10s1 import core as s1

    return s1.seed_set(f"p10ir-bridge-{draw}", bridge_base(draw, cfg))


def rehearsal_seeds(cfg: Mapping[str, Any] | None = None) -> Any:
    from studies.p10s1 import core as s1

    return s1.seed_set("p10ir-rehearsal", int((cfg or load_config())["seeds"]["rehearsal_base"]))


def test_seeds(k: int = 0, cfg: Mapping[str, Any] | None = None) -> Any:
    """Unit tests and test mode: sets at 938001 + 100 k (k = 0..8), inside the registry's test range."""
    from studies.p10s1 import core as s1

    lo, hi = (cfg or load_config())["seeds"]["test_range"]
    base = int(lo) + 100 * k
    if not 0 <= k <= 8 or base + 99 > int(hi):
        raise ValueError("test seed set out of range (0..8)")
    return s1.seed_set(f"p10ir-test-{k}", base)


def p10s1_draw_seeds(draw: int, cfg: Mapping[str, Any] | None = None) -> Any:
    """P10-S1's registered draw ``draw`` (the declared re-use of section 5)."""
    from studies.p10s1 import core as s1

    if not 1 <= draw <= 5:
        raise ValueError("P10-S1's registered draws are 1..5")
    return s1.registered_draw_seeds(draw)


def seed_set_values(seeds: Any) -> frozenset[int]:
    """Every integer a set uses (P10-S1's ``set_values``: data and null seeds, H8, ten masks, index seed)."""
    from studies.p10s1 import core as s1

    return s1.set_values(seeds)


def i64_seeds(cfg: Mapping[str, Any] | None = None, *, test: bool = False) -> list[int]:
    """The three I64 index seeds: the registered 298001-298003, or (``test``: rehearsal and unit tests) the test-range values, never the registered ones."""
    return [int(s) for s in (cfg or load_config())["seeds"]["test_index_seeds" if test else "index_seeds"]]


# --- time, envelope, records, ledger --------------------------------------------------------------------------------------------
def utc_stamp(now: datetime | None = None) -> str:
    return (now or datetime.now(UTC)).strftime("%Y%m%dT%H%M%S%fZ")


def envelope(kind: str) -> dict[str, Any]:
    if kind not in RECORD_KINDS:
        raise ValueError(f"unknown record kind {kind!r}")
    return {"kind": kind, "schema": SCHEMA, "study": STUDY}


def check_envelope(record: Mapping[str, Any], kind: str | None = None) -> None:
    if record.get("study") != STUDY or record.get("schema") != SCHEMA or record.get("kind") not in RECORD_KINDS:
        raise ValueError("P10IR record needs study, schema and a registered kind")
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
        raise ValueError(f"not a P10IR record: {path}")
    check_envelope(rec, kind)
    return rec


class LedgerRefused(RuntimeError):
    """A stage cannot start: the remainder of its cap is smaller than the stage's own cap."""


class Ledger:
    """Charged wall time of the study (rehearsal and every registered stage), appended to one JSON file. The cap of a stage is a config value in hours, times 3,600."""

    def __init__(self, path: Path, total_seconds: float) -> None:
        if not math.isfinite(total_seconds) or total_seconds <= 0:
            raise ValueError("the cap must be a positive number of seconds")
        self.path, self.total_seconds = path, float(total_seconds)

    def entries(self) -> list[dict[str, Any]]:
        if not self.path.is_file():
            return []
        data = read_json(self.path)
        if not isinstance(data, dict) or data.get("study") != STUDY or data.get("kind") != "ledger":
            raise ValueError(f"not a P10IR ledger: {self.path}")
        return list(data["entries"])

    def charged(self, stage: str | None = None) -> float:
        return float(sum(float(e["seconds"]) for e in self.entries() if stage is None or e["stage"] == stage))

    def remaining(self) -> float:
        return max(0.0, self.total_seconds - self.charged())

    def require_room(self, stage: str, stage_cap_seconds: float) -> None:
        if not math.isfinite(stage_cap_seconds) or stage_cap_seconds <= 0:
            raise LedgerRefused(f"stage {stage}: the stage cap must be a positive number")
        if self.remaining() <= 0:
            raise LedgerRefused(f"stage {stage}: the total cap of {self.total_seconds:.0f} s is spent; the stage is PAUSED and the extension is the human lead's")

    def charge(self, stage: str, run: str, seconds: float) -> None:
        entries = self.entries()
        entries.append({"stage": stage, "run": run, "seconds": max(0.0, float(seconds)), "utc": datetime.now(UTC).isoformat()})
        self.path.parent.mkdir(parents=True, exist_ok=True)
        write_json(self.path, {"study": STUDY, "kind": "ledger", "schema": SCHEMA, "total_seconds": self.total_seconds, "entries": entries})


def cap_hours(stage_name: str, cfg: Mapping[str, Any] | None = None) -> float:
    """The cap in charged hours of ``a1``, ``a2``, ``rehearsal`` or ``total`` (config ``[caps]``)."""
    c = (cfg or load_config())["caps"]
    key = f"{stage_name}_hours"
    if key not in c:
        raise ValueError(f"no cap named {stage_name!r}")
    return float(c[key])


def caps_provisional(cfg: Mapping[str, Any] | None = None) -> bool:
    return bool((cfg or load_config())["caps"]["provisional"])


def propose_cap_hours(charged_hours: float, projected_remaining_hours: float) -> float:
    """Section 12: a resource cap is set after the rehearsal as charged + 2 x projected remaining. Printed for the human lead; nothing writes it to the config."""
    if charged_hours < 0 or projected_remaining_hours < 0:
        raise ValueError("hours are not negative")
    return charged_hours + 2.0 * projected_remaining_hours


def iter_checkpoints(cfg: Mapping[str, Any] | None = None) -> Iterable[tuple[CellSpec, int]]:
    for c in cell_specs(cfg):
        for u in c.checkpoints():
            yield c, u
