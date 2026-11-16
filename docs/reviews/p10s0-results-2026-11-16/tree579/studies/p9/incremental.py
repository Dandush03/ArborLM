# ruff: noqa: E501
"""P9 Lane D (package I5): phase A and phase B arms, replay, fresh optimizer at V1, and the Lane D
measurements.

Specification: ADR-0017 section 8.5 (incremental; 16,384 slots; A and B are 4,096 disjoint facts each),
15.1 item 4 (replay adds 16 replayed A contexts to the 16 B contexts of each update; the update count is
unchanged). Training itself is ``train.train_cell`` driven through ``train.TrainJob``; this module builds
the jobs and measures. Phase A is the D1 cells; phase B the D2 cells (six trained arms plus the joint
bound; exact retrieval by append is ``exact_append_control``, built on ``controls.exact_retrieval``).

Arms (``Cell.lane_d_arm``): ``phaseA`` (D1: flat, learned tree, dense), ``sequential`` (all addition
parameters train, from V1), ``memory_only`` (flat only: keys and values train, projections and gate
frozen), ``replay`` (flat and dense: B's E exposures plus one replayed A context per B context,
``core.contexts_per_update``; updates = ``core.updates``; compared only with each other and the
bound), ``joint`` (flat from initialization on A u B, ``core.LANE_D_JOINT_FACTS`` facts, so twice the
updates of one phase). Every phase-B arm starts from V1's parameters with a FRESH optimizer state (ADR
8.5, ``restore_optimizer=False``); V1 also stores the optimizer state, for the restoration test only.

Definitions fixed here where the ADR leaves a measurement open (reported to the lead):

* V1 is the D1 cell's snapshot at its own ``U`` (``core.updates``); ``phase_b_job`` refuses a snapshot
  directory with another update number.
* ``changed_between``: a slot is changed when its key row or its value row differs bit for bit; ``bytes``
  adds up, over every addition tensor, the bytes of the rows that differ (a 0-dimensional tensor counts
  its element size), so projections, gate and router changes of the sequential arms are counted and the
  memory-only arm's bytes are keys and values only. ``changed_bytes_keys_values`` (lead ruling b) reports
  the keys and values tables alone beside it. Dense has no slots: 0 slots, and the bytes of its
  changed rows.
* ``support_overlap``: Jaccard index of the union of slot ids in the minimal supports of A facts and
  of B facts (``evaluate.SupportResult.slots``); the share of B's support slots that A's supports also use
  is reported beside it by ``support_overlap_detail``. PENDING LEAD REVIEW (the ADR does not define it).
* ``logical_lookup_work``: key products per query (``core.logical_key_products``) times the queries of
  the training run: the contexts trained on times the number of read positions of the model (63 at R0).
  Dense has no key products (0). Logical work only, never a speedup.
* ``measure_arm`` reads evaluation records written by ``evaluate`` (``core.eval_path``) and the train
  record; it does not evaluate and refuses a rehearsal-mode run. The joint bound has no V1: its
  ``a0_acc`` is None and its changed counts are 0.

Self-check only: not independent review, not Astra validation, not human approval.
"""

import argparse
import dataclasses
import json
import math
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import torch

from . import controls, core
from . import data as data_mod
from .core import Cell
from .data import StudyData
from .train import TrainJob

if TYPE_CHECKING:
    from torch import Tensor

    from arborlm.p4_model import Backbone

PHASE_B_ARMS = ("sequential", "memory_only", "replay", "joint")
MEMORY_ONLY_GROUPS = ("keys", "values")
PANELS = core.PANELS
ADDITION_PREFIX = "addition."
EXACT_BYTES_PER_FACT = 6  # five identifier bytes and the answer byte appended per stored fact
EXACT_LABEL = "exact_retrieval_append"


class MissingDependency(FileNotFoundError):
    """A phase-B job was asked to start without the V1 snapshot of the D1 cell it depends on."""


# --- jobs --------------------------------------------------------------------------------------------
def _seed_arguments(data: StudyData, mode: str) -> tuple[int | None, int, int]:
    """As ``train.prepare_job``: registered runs use the cell's own initialization seed; every other
    mode uses the data draw's rehearsal-namespace seeds."""
    seeds = data.seeds
    return (None if mode == "registered" else seeds.facts), seeds.r1_codes, seeds.branch_hash


def _check_lane_d(cell: Cell, arms: Sequence[str], what: str) -> None:
    if cell.lane_d_arm not in arms:
        raise ValueError(f"{cell.label} is not a {what} cell (lane_d_arm={cell.lane_d_arm!r})")


def phase_a_job(
    cell: Cell, data: StudyData, backbone: "Backbone", run_dir: Path, exposure: int, mode: str
) -> TrainJob:
    """TrainJob of a D1 cell: E exposures of set A from initialization; V1 = the snapshot at U."""
    _check_lane_d(cell, ("phaseA",), "phase A (D1)")
    init_seed, r1_seed, branch_seed = _seed_arguments(data, mode)
    return TrainJob(
        cell=cell,
        exposure=exposure,
        mode=mode,
        data=data,
        stream=data_mod.training_stream_for(data, cell),
        backbone=backbone,
        out_dir=core.cell_dir(run_dir, cell.label),
        init_snapshot=None,
        restore_optimizer=False,
        trainable_groups=None,
        init_seed=init_seed,
        r1_seed=r1_seed,
        branch_seed=branch_seed,
    )


def v1_snapshot_path(run_dir: Path, d1_label: str, exposure: int) -> Path:
    """Snapshot directory of V1: the D1 cell's snapshot at ``core.updates(d1, exposure)``."""
    d1 = core.parse_label(d1_label)
    _check_lane_d(d1, ("phaseA",), "phase A (D1)")
    return core.snapshot_dir(run_dir, d1_label, core.updates(d1, exposure))


def _require_v1(cell: Cell, v1_snapshot: Path | None, exposure: int) -> Path:
    if not cell.depends_on:
        raise ValueError(f"{cell.label} has no D1 dependency")
    dependency = cell.depends_on[0]
    if v1_snapshot is None or not (Path(v1_snapshot) / "model.pt").is_file():
        raise MissingDependency(
            f"{cell.label} cannot start: its D1 dependency {dependency} has no V1 snapshot at {v1_snapshot} (no model.pt)"
        )
    v1 = Path(v1_snapshot)
    expected = core.snapshot_stem(core.matched_updates(cell.facts, exposure))
    if v1.name != expected:
        raise ValueError(f"V1 of {dependency} is its snapshot at U ({expected}), not {v1.name}")
    record = v1 / "snapshot.json"
    if record.is_file():
        label = core.read_record(record, "snapshot")["label"]
        if label != dependency:
            raise ValueError(
                f"{v1} is a snapshot of {label}, but {cell.label} depends on {dependency}"
            )
    return v1


def phase_b_job(
    cell: Cell,
    data: StudyData,
    backbone: "Backbone",
    run_dir: Path,
    v1_snapshot: Path | None,
    exposure: int,
    mode: str,
) -> TrainJob:
    """TrainJob of a D2 cell from ``v1_snapshot`` (V1 of the D1 cell named by ``cell.depends_on``):
    model parameters only, fresh optimizer (``restore_optimizer=False``); memory-only sets
    ``trainable_groups=("keys", "values")``; replay adds set-A contexts (the stream's replay ids); joint
    (no dependency, ``v1_snapshot`` must be None) starts from initialization on A then B ids. Raises
    ``MissingDependency`` naming the D1 cell when the V1 snapshot is absent. ``v1_snapshot`` widens the
    stub's ``Path`` to ``Path | None`` for the joint bound."""
    _check_lane_d(cell, PHASE_B_ARMS, "phase B (D2)")
    if cell.lane_d_arm == "memory_only" and cell.arch != "flat":
        raise ValueError("memory-only is defined for the flat memory only")
    init: Path | None
    if cell.lane_d_arm == "joint":
        if v1_snapshot is not None:
            raise ValueError("the joint bound starts from initialization and has no V1")
        init = None
    else:
        init = _require_v1(cell, v1_snapshot, exposure)
    init_seed, r1_seed, branch_seed = _seed_arguments(data, mode)
    return TrainJob(
        cell=cell,
        exposure=exposure,
        mode=mode,
        data=data,
        stream=data_mod.training_stream_for(data, cell),
        backbone=backbone,
        out_dir=core.cell_dir(run_dir, cell.label),
        init_snapshot=init,
        restore_optimizer=False,
        trainable_groups=MEMORY_ONLY_GROUPS if cell.lane_d_arm == "memory_only" else None,
        init_seed=init_seed,
        r1_seed=r1_seed,
        branch_seed=branch_seed,
    )


# --- replay ------------------------------------------------------------------------------------------
_REPLAY_CACHE: list[tuple[StudyData, Any]] = []


def _replay_stream(data: StudyData) -> Any:
    for held, stream in _REPLAY_CACHE:
        if held is data:
            return stream
    template = next(
        c
        for c in core.cells()
        if c.lane_d_arm == "replay" and c.arch == "flat" and c.seed == core.INIT_SEEDS[0]
    )
    stream = data_mod.training_stream_for(
        data, dataclasses.replace(template, facts=data.lane_d_set_size)
    )
    del _REPLAY_CACHE[:]
    _REPLAY_CACHE.append((data, stream))
    return stream


def replay_contexts(data: StudyData, update: int) -> "Tensor":
    """``[16, 64] int64`` replayed set-A contexts of 1-based ``update`` (pure function of the update):
    the replay half of the batch every replay arm trains on at that update."""
    batch = _replay_stream(data).batch(update)
    if batch.replay_tokens is None:
        raise ValueError("the replay stream has no replayed contexts")
    tokens: Tensor = batch.replay_tokens
    return tokens


# --- measurements ----------------------------------------------------------------------------------------
@dataclass
class LaneDMeasurement:
    """Accuracy after a phase on a primary panel. ``a_acc`` and ``b_acc`` are accuracies on the A and B
    facts; ``a0_acc`` is accuracy on A after phase A (the cell's own D1); ``changed_slots`` and
    ``changed_bytes`` count key and value rows that differ between V1 and V2 (0 slots for dense: its
    changed bytes are counted instead); ``support_overlap`` is the overlap of the minimal supports of A and
    B facts (``evaluate.minimal_supports``; see ``support_overlap_detail``)."""

    label: str
    panel: str
    a_acc: float
    b_acc: float
    a0_acc: float | None
    changed_slots: int
    changed_bytes: int
    support_overlap: float | None
    updates: int
    examples: int
    logical_lookup_work: int
    changed_bytes_keys_values: int = 0  # keys and values tables only, reported beside ``changed_bytes``


def _addition_state(snapshot: Path) -> dict[str, "Tensor"]:
    payload = torch.load(snapshot / "model.pt", weights_only=True, map_location="cpu")
    return {
        name[len(ADDITION_PREFIX) :]: tensor.contiguous()
        for name, tensor in payload["model"].items()
        if name.startswith(ADDITION_PREFIX)
    }


def _row_bytes(t: "Tensor") -> "Tensor":
    rows = int(t.shape[0]) if t.ndim else 1
    return t.reshape(-1).view(torch.uint8).reshape(rows, -1)


def _changed_rows(a: "Tensor", b: "Tensor") -> list[int]:
    if a.shape != b.shape or a.dtype != b.dtype:
        raise ValueError("snapshots differ in the shape or dtype of an addition tensor")
    if a.numel() == 0:
        return []
    return [
        int(i) for i in (_row_bytes(a) != _row_bytes(b)).any(dim=1).nonzero().reshape(-1).tolist()
    ]


def changed_detail(v1_snapshot: Path, v2_snapshot: Path) -> dict[str, Any]:
    """Per addition tensor, the changed rows and bytes between two snapshots, and the slot totals."""
    one, two = _addition_state(Path(v1_snapshot)), _addition_state(Path(v2_snapshot))
    if one.keys() != two.keys():
        raise ValueError("snapshots have different addition tensors")
    tensors: dict[str, Any] = {}
    slot_rows: set[int] = set()
    total_bytes = 0
    for name in sorted(one):
        rows = _changed_rows(one[name], two[name])
        count = int(one[name].shape[0]) if one[name].ndim else 1
        row_size = one[name].element_size() * (one[name].numel() // count) if count else 0
        nbytes = len(rows) * row_size
        tensors[name] = {"changed_rows": len(rows), "changed_bytes": nbytes}
        total_bytes += nbytes
        if name in ("keys", "values"):
            slot_rows.update(rows)
    return {"slots": len(slot_rows), "bytes": total_bytes, "tensors": tensors}


def keys_values_bytes(detail: Mapping[str, Any]) -> int:
    """Changed bytes of the ``keys`` and ``values`` tables only (lead ruling b: reported beside the
    all-addition-tensor count ``detail['bytes']``)."""
    tensors = detail["tensors"]
    return int(sum(tensors[name]["changed_bytes"] for name in ("keys", "values") if name in tensors))


def changed_between(v1_snapshot: Path, v2_snapshot: Path) -> tuple[int, int]:
    """``(slots, bytes)`` whose key or value rows differ between V1 and V2; bytes count every changed row
    of every addition tensor (see the module docstring). Dense: ``(0, bytes of its changed rows)``."""
    detail = changed_detail(v1_snapshot, v2_snapshot)
    return int(detail["slots"]), int(detail["bytes"])


def forgetting(a0_acc: float, a_acc: float) -> float:
    """a_A^0 - a_A."""
    return a0_acc - a_acc


def logical_lookup_work(arch: str, slots: int, queries: int) -> int:
    """Logical key products over ``queries`` (``core.logical_key_products``); logical work only. The
    dense adapter has no key products: 0."""
    if queries < 0:
        raise ValueError("queries must be non-negative")
    if arch == "dense":
        return 0
    return queries * core.logical_key_products(arch, slots)


def lane_d_gate(a0_accuracies: dict[str, float]) -> dict[str, bool]:
    """Per D1 label: phase-A accuracy >= ``core.LANE_D_A0_MIN`` (else the arm is NOT_EVALUATED)."""
    return {label: acc >= core.LANE_D_A0_MIN for label, acc in a0_accuracies.items()}


def support_overlap_detail(
    supports_a: Sequence[Sequence[int]], supports_b: Sequence[Sequence[int]]
) -> dict[str, Any]:
    """Overlap of the slot sets used by the minimal supports of A facts and of B facts (each argument is
    ``SupportResult.slots``: one slot list per fact)."""
    slots_a = {int(s) for fact in supports_a for s in fact}
    slots_b = {int(s) for fact in supports_b for s in fact}
    shared, union = len(slots_a & slots_b), len(slots_a | slots_b)
    return {
        "slots_a": len(slots_a),
        "slots_b": len(slots_b),
        "shared": shared,
        "union": union,
        "jaccard": shared / union if union else None,
        "share_of_b_in_a": shared / len(slots_b) if slots_b else None,
    }


def _accuracy(run_dir: Path, label: str, update: int, stream: str) -> float:
    path = core.eval_path(run_dir, label, update, stream)
    if not path.is_file():
        raise FileNotFoundError(
            f"missing evaluation record {path} (run evaluate for {label} first)"
        )
    record = core.read_record(path, "eval")
    value = float(record["accuracy"])
    if not math.isfinite(value):
        raise ValueError(f"non-finite accuracy in {path}")
    return value


def _stream(panel: str, which: str) -> str:
    return f"lane_d_{panel.lower()}_{which}"


def measure_arm(
    cell: Cell,
    run_dir: Path,
    data: StudyData,
    experiments_root: Path,
    exposure: int,
    *,
    supports: Mapping[str, tuple[Sequence[Sequence[int]], Sequence[Sequence[int]]]] | None = None,
) -> list[LaneDMeasurement]:
    """Measure one D2 cell on panels A and B for sets A and B from the evaluation records of ``evaluate``
    (the phase-end snapshot of this cell and of its D1 cell) and the cell's train record. ``supports``
    maps a panel to ``(A supports, B supports)`` (``SupportResult.slots`` of the two sets, computed by
    ``evaluate.minimal_supports``) for the overlap; without it the overlap is None. ``data`` and
    ``experiments_root`` are accepted for signature compatibility; nothing is evaluated here."""
    _check_lane_d(cell, PHASE_B_ARMS, "phase B (D2)")
    train_path = core.cell_dir(run_dir, cell.label) / "train.json"
    if not train_path.is_file():
        raise FileNotFoundError(f"missing train record {train_path}")
    train = core.read_record(train_path, "train")
    if train.get("mode") == "rehearsal":
        raise ValueError("rehearsal runs write no accuracy and are never measured")
    update = core.updates(cell, exposure)
    joint = cell.lane_d_arm == "joint"
    d1_label = None if joint else cell.depends_on[0]
    v1_update = core.matched_updates(cell.facts, exposure)
    slots = nbytes = kv_bytes = 0
    if not joint and d1_label is not None:
        detail = changed_detail(
            core.snapshot_dir(run_dir, d1_label, v1_update),
            core.snapshot_dir(run_dir, cell.label, update),
        )
        slots, nbytes, kv_bytes = int(detail["slots"]), int(detail["bytes"]), keys_values_bytes(detail)
    from .model import AdditionSpec

    queries = int(train["examples"]) * len(AdditionSpec.from_cell(cell).read_positions)
    work = logical_lookup_work(cell.arch, cell.slots, queries)
    out = []
    for panel in PANELS:
        overlap = None
        if supports is not None and panel in supports:
            overlap = support_overlap_detail(*supports[panel])["jaccard"]
        out.append(
            LaneDMeasurement(
                label=cell.label,
                panel=panel,
                a_acc=_accuracy(run_dir, cell.label, update, _stream(panel, "A")),
                b_acc=_accuracy(run_dir, cell.label, update, _stream(panel, "B")),
                a0_acc=None
                if d1_label is None
                else _accuracy(run_dir, d1_label, v1_update, _stream(panel, "A")),
                changed_slots=slots,
                changed_bytes=nbytes,
                support_overlap=overlap,
                updates=int(train["run_updates"]),
                examples=int(train["examples"]),
                logical_lookup_work=work,
                changed_bytes_keys_values=kv_bytes,
            )
        )
    return out


# --- exact retrieval by append -----------------------------------------------------------------------------
def _accuracy_of(scores: core.AnswerScores) -> float:
    return float(scores.correct.float().mean())


def exact_append_control(data: StudyData) -> list[LaneDMeasurement]:
    """The append-only exact retrieval arm of ADR 8.5 (no training): a dictionary of set A (phase A) is
    extended with set B's entries (phase B) and nothing stored is rewritten, so A is untouched. Per panel:
    ``a0_acc`` is A's accuracy with the A-only dictionary, ``a_acc`` and ``b_acc`` use the appended
    dictionary. ``changed_slots`` is the number of appended entries and ``changed_bytes`` six bytes per
    entry (five identifier bytes and the answer byte); updates, examples and lookup work are 0."""
    n = data.lane_d_set_size
    ids_a, ids_b = torch.arange(0, n), torch.arange(n, 2 * n)
    both = torch.cat([ids_a, ids_b])
    out = []
    for panel in PANELS:
        stream_a = data.streams[_stream(panel, "A")]
        stream_b = data.streams[_stream(panel, "B")]
        out.append(
            LaneDMeasurement(
                label=EXACT_LABEL,
                panel=panel,
                a_acc=_accuracy_of(controls.exact_retrieval(data.lane_d, stream_a, both)),
                b_acc=_accuracy_of(controls.exact_retrieval(data.lane_d, stream_b, both)),
                a0_acc=_accuracy_of(controls.exact_retrieval(data.lane_d, stream_a, ids_a)),
                changed_slots=n,
                changed_bytes=n * EXACT_BYTES_PER_FACT,
                support_overlap=None,
                updates=0,
                examples=0,
                logical_lookup_work=0,
                changed_bytes_keys_values=n * EXACT_BYTES_PER_FACT,
            )
        )
    return out


# --- command line --------------------------------------------------------------------------------------------
def _load_context(args: argparse.Namespace, *, backbone: bool) -> tuple[Cell, StudyData, Any, Path]:
    """The cell, the data draw and (optionally) the verified backbone; needs the git-ignored
    ``experiments/`` directory."""
    from arborlm import p8_core

    cell = core.parse_label(args.label)
    root = Path(args.experiments_root) if args.experiments_root else core.default_experiments_root()
    seeds = (
        core.registered_seeds() if args.mode == "registered" else core.rehearsal_seeds(args.draw)
    )
    loaded = p8_core.load_backbone(cell, root)[0] if backbone else None
    study = data_mod.build_study_data(seeds, core.load_trained_corpus(root))
    return cell, study, loaded, root


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m studies.p9.incremental", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("phase-a", "phase-b", "measure"):
        p = sub.add_parser(name)
        p.add_argument("--label", required=True)
        p.add_argument("--run-dir", required=True)
        p.add_argument("--experiments-root", default=None)
        p.add_argument("--exposure", type=int, default=core.DEFAULT_EXPOSURE)
        p.add_argument(
            "--mode", choices=("registered", "calibration", "rehearsal"), default="calibration"
        )
        p.add_argument("--draw", type=int, default=0, help="rehearsal seed draw")
        if name != "measure":
            p.add_argument("--max-updates", type=int, default=None)
        if name == "phase-b":
            p.add_argument(
                "--v1",
                default=None,
                help="V1 snapshot directory (default: the D1 cell's snapshot at U)",
            )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI ``uv run --locked python -m studies.p9.incremental {phase-a,phase-b,measure} ...``. ``phase-a``
    and ``phase-b`` train one cell (as ``studies.p9.train cell`` does) and print one line of non-loss,
    non-accuracy facts; ``measure`` prints the measurements of a D2 cell from existing evaluation records
    and refuses a rehearsal mode."""
    from . import train

    args = _parser().parse_args(argv)
    run_dir = Path(args.run_dir)
    if args.command == "measure" and args.mode == "rehearsal":
        print("rehearsal runs write no accuracy and are never measured", file=sys.stderr)
        return 2
    train._configure()
    cell, study, backbone, root = _load_context(args, backbone=args.command != "measure")
    if args.command == "measure":
        rows = measure_arm(cell, run_dir, study, root, args.exposure)
        print(json.dumps([dataclasses.asdict(r) for r in rows], sort_keys=True))
        return 0
    try:
        if args.command == "phase-a":
            job = phase_a_job(cell, study, backbone, run_dir, args.exposure, args.mode)
        else:
            v1 = None
            if cell.lane_d_arm != "joint":
                v1 = (
                    Path(args.v1)
                    if args.v1
                    else v1_snapshot_path(run_dir, cell.depends_on[0], args.exposure)
                )
            job = phase_b_job(cell, study, backbone, run_dir, v1, args.exposure, args.mode)
    except MissingDependency as exc:
        print(f"MISSING DEPENDENCY: {exc}", file=sys.stderr)
        return 3
    job.max_updates = args.max_updates
    record = train.train_cell(job)
    if args.mode == "rehearsal":
        print((job.out_dir / "rehearsal.json").read_text(encoding="utf-8"))
    else:
        print(
            json.dumps(
                {
                    "label": record["label"],
                    "status": record["status"],
                    "record": str(job.out_dir / "train.json"),
                }
            )
        )
    return 0 if record["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

__all__ = [
    "LaneDMeasurement",
    "MissingDependency",
    "changed_between",
    "changed_detail",
    "exact_append_control",
    "forgetting",
    "keys_values_bytes",
    "lane_d_gate",
    "logical_lookup_work",
    "main",
    "measure_arm",
    "phase_a_job",
    "phase_b_job",
    "replay_contexts",
    "support_overlap_detail",
    "v1_snapshot_path",
]
