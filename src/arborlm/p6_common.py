"""Shared P6-E machinery: cell loading (real P5 snapshots or a tiny synthetic fixture), stage
budgets and small helpers. No scientific decision lives here.

Status: SPEC: HUMAN-APPROVED (ADR-0011); implementation self-checked only.
"""

import struct
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import torch
from torch import Tensor

from .io import file_sha256, read_json
from .p2_config import BACKBONES, CONTROL, ORDERS
from .p2_config import Cell as ParentCell
from .p5_config import FIXED, FLAT, LEARNED, MEMORIES, PARENT_SUITE, SEEDS, STEPS, Cell
from .p5_model import Model, evaluate, state_digest

SPEC = "docs/decisions/ADR-0011-p6-retrieval-optimization-and-routing-fidelity.md"
FAMILY = "P6E_RETRIEVAL_OPTIMIZATION"
P5_RESULTS = Path("results/p5-2026-11-13")
KINDS = MEMORIES  # ("flat", "fixed_tree", "learned_tree")
TREE_KINDS = (FIXED, LEARNED)

Pair = tuple[int, int, int]

# Plain statements of limits that no code change addresses (audit MINOR 5, NOTES 3 and 7). They are
# copied verbatim into every P6-E stage manifest and timing record.
KNOWN_LIMITS = (
    "Fingerprint binding (data pointer, version counter, shape) does not detect writes through "
    "`.data` between the pre- and post-schedule full-hash checks; only the full SHA-256 checks "
    "before and after each timing schedule can detect them.",
    "`slot_offsets` (arange(256)) is an additional load-time cache of the tree variants that "
    "section 3.2 does not list; the reference builds it on every call (cost about 1 microsecond).",
    "RNG-unchanged checks that sit inside an isolated-RNG block cannot observe RNG use, because "
    "the block restores the generator state on exit; no variant uses RNG.",
)


def pairs() -> list[Pair]:
    """The 27 registered parent/seed pairs in P5 cell-index order."""
    return [(b, o, s) for b in BACKBONES for o in ORDERS for s in SEEDS]


def pair_label(pair: Pair) -> str:
    return f"b{pair[0]}-o{pair[1]}-s{pair[2]}"


def pair_index(pair: Pair) -> int:
    return Cell(pair[0], pair[1], pair[2], FLAT).index


def bits_equal_float(a: float, b: float) -> bool:
    return struct.pack("!d", a) == struct.pack("!d", b)


@dataclass
class StageBudget:
    """Active worker time for one stage. No transfer of unused time between stages."""

    cap_seconds: float
    worker_cap_seconds: float | None = None
    now: Any = time.monotonic
    start: float = field(init=False)

    def __post_init__(self) -> None:
        self.start = self.now()

    def elapsed(self) -> float:
        return float(self.now() - self.start)

    def remaining(self) -> float:
        return self.cap_seconds - self.elapsed()

    def worker_budget(self) -> float:
        left = self.remaining()
        if left <= 0:
            raise TimeoutError("P6 stage wall-time cap exhausted")
        return left if self.worker_cap_seconds is None else min(self.worker_cap_seconds, left)


@dataclass
class CellSource:
    pair: Pair
    models: dict[str, Model]
    evidence: dict[str, dict[str, Any]]
    recorded: dict[str, dict[str, Any]]
    panel: Tensor
    train: Tensor
    expected_targets: int
    synthetic: bool

    @property
    def label(self) -> str:
        return pair_label(self.pair)

    def digests(self) -> dict[str, str]:
        return {kind: state_digest(model) for kind, model in self.models.items()}

    def files_unchanged(self) -> bool:
        """Re-hash the snapshot files (real cells only) against the recorded P5 hashes."""
        if self.synthetic:
            return True
        for kind, record in self.evidence.items():
            path = Path(record["path"])
            if (
                file_sha256(path / "state.pt") != record["state_sha256"]
                or file_sha256(path / "index.json") != record["index_sha256"]
                or record["state_sha256"] != self.recorded[kind]["state_sha256"]
            ):
                return False
            parent = record["checkpoint_identity"]["parent"]
            for provenance in (parent, parent["upstream_p3"]):
                original = Path(provenance["checkpoint_path"])
                if (
                    file_sha256(original / "state.pt") != provenance["checkpoint_state_sha256"]
                    or file_sha256(original / "index.json") != provenance["checkpoint_index_sha256"]
                ):
                    return False
        return True


def locate_quality(p5_suite: Path) -> Path:
    found = sorted((p5_suite / "quality").glob("P5QUALITY-*"))
    if len(found) != 1:
        raise ValueError("expected exactly one P5 quality stage under the parent suite")
    return found[0]


def load_real_cell(
    pair: Pair,
    *,
    p5_suite: Path,
    output_root: Path,
    p5_results: Path,
    data_dir: Path,
    run: Path,
) -> CellSource:
    """Restore the three final memory snapshots of one parent/seed with P5's own loader.

    This only restores and verifies. Nothing is timed here.
    """
    from .hierarchy_ablation import _timing_models
    from .p5_data import load_frozen
    from .records import record_environment

    b, o, seed = pair
    quality = locate_quality(p5_suite)
    environment = record_environment(run, family=FAMILY)
    # P5 recorded absolute checkpoint paths in its provenance, so the P4 suite path must be too.
    p4_suite = (output_root / PARENT_SUITE).resolve()
    models, evidence = _timing_models(quality.resolve(), p4_suite, b, o, seed, environment)
    recorded: dict[str, dict[str, Any]] = {}
    for kind in KINDS:
        cell = Cell(b, o, seed, kind)
        result = read_json(p5_results / cell.label / "result.json")
        if (
            result["cell"] != cell.fields()
            or result["completed_steps"] != STEPS
            or result["final"]["target_tokens"] != 32768
        ):
            raise ValueError(f"P5 compact record does not match {cell.label}")
        recorded[kind] = {
            "nll": result["final"]["nll"],
            "state_sha256": result["checkpoint_state_sha256"][f"checkpoint-{STEPS}"],
        }
        if evidence[kind]["state_sha256"] != recorded[kind]["state_sha256"]:
            raise ValueError(f"snapshot hash differs from the compact P5 record: {cell.label}")
    dataset_hash = read_json(quality / "manifest.json")["dataset_manifest_sha256"]
    train, _, validation, _ = load_frozen(quality / "frozen-data", dataset_hash)
    frozen_acquisition = file_sha256(quality / "frozen-data" / "acquisition.json")
    if (data_dir / "manifest.json").is_file():
        if file_sha256(data_dir / "manifest.json") != frozen_acquisition:
            raise ValueError("--data-dir acquisition manifest differs from the frozen P5 data")
    else:
        raise ValueError("--data-dir does not contain the WikiText-2 acquisition manifest")
    # P5's loader returns every P5 variant (including the dense baseline); P6-E uses, and must
    # re-verify, only the three memory kinds.
    kept = {kind: models[kind] for kind in KINDS}
    kept_evidence = {kind: evidence[kind] for kind in KINDS}
    for kind, model in kept.items():
        model.eval()
        kept_evidence[kind]["recorded_final_nll"] = recorded[kind]["nll"]
    return CellSource(pair, kept, kept_evidence, recorded, validation, train, 32768, False)


def load_synthetic_cell(pair: Pair, *, rows: int = 16) -> CellSource:
    """Tiny random fixture with the same classes and shapes (dry-run and tests only)."""
    from .p2_model import FollowupModel
    from .p4_model import extract

    backbone = extract(FollowupModel(ParentCell(pair[0], 201, pair[1], CONTROL)))
    generator = torch.Generator().manual_seed(9000 + pair_index(pair))
    panel = torch.randint(0, 256, (rows, 65), generator=generator)
    train = torch.randint(0, 256, (32, 65), generator=generator)
    models = {kind: Model(Cell(pair[0], pair[1], pair[2], kind), backbone) for kind in KINDS}
    evidence: dict[str, dict[str, Any]] = {}
    recorded: dict[str, dict[str, Any]] = {}
    for kind, model in models.items():
        model.eval()
        nll = evaluate(model, panel, rows * 64)["nll"]
        recorded[kind] = {"nll": nll, "state_sha256": state_digest(model)}
        evidence[kind] = {"synthetic": True, "recorded_final_nll": nll}
    return CellSource(pair, models, evidence, recorded, panel, train, rows * 64, True)


def synthetic_pairs(count: int) -> list[Pair]:
    return pairs()[:count]


@dataclass
class StudyArgs:
    """Parameters shared by the stages and their workers (JSON round-trippable)."""

    data_dir: Path
    parent_suite: Path
    output_root: Path
    results_root: Path
    p5_results: Path = P5_RESULTS
    synthetic: bool = False
    pair_count: int = 27
    rounds: int = 8
    panel_rows: int = 16
    equivalence_run: str | None = None
    screen_run: str | None = None
    confirm_run: str | None = None
    supersede: str | None = None
    supersede_reason: str | None = None

    def __post_init__(self) -> None:
        registered = (self.pair_count, self.rounds) == (27, 8) and not self.synthetic
        if not registered and not self.synthetic:
            raise ValueError("pair count and repetition counts are fixed outside a dry run")
        if not 1 <= self.pair_count <= 27 or not 1 <= self.rounds <= 8:
            raise ValueError("invalid pair or round count")
        if (self.supersede is None) != (not self.supersede_reason):
            raise ValueError("--supersede and --reason must be given together")

    @property
    def dry_run(self) -> bool:
        return self.synthetic

    def pair_list(self) -> list[Pair]:
        return pairs()[: self.pair_count]

    def to_json(self) -> dict[str, Any]:
        return {k: (str(v) if isinstance(v, Path) else v) for k, v in self.__dict__.items()}

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "StudyArgs":
        paths = ("data_dir", "parent_suite", "output_root", "results_root", "p5_results")
        fields: dict[str, Any] = {k: (Path(v) if k in paths else v) for k, v in data.items()}
        return cls(**fields)


def compact_evidence(source: CellSource) -> dict[str, Any]:
    keep = (
        "path",
        "state_sha256",
        "index_sha256",
        "quality_run_id",
        "recorded_final_nll",
        "synthetic",
    )
    return {
        kind: {k: v for k, v in rec.items() if k in keep} for kind, rec in source.evidence.items()
    }


def load_cell(args: StudyArgs, pair: Pair, run: Path) -> CellSource:
    if args.synthetic:
        return load_synthetic_cell(pair, rows=args.panel_rows)
    return load_real_cell(
        pair,
        p5_suite=args.parent_suite,
        output_root=args.output_root,
        p5_results=args.p5_results,
        data_dir=args.data_dir,
        run=run,
    )
