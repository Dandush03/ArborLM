# ruff: noqa: E501
"""P10IS3 parents: the nine frozen P3 control backbones used by P4 and P5 (B = 101..103, O = 301..303), read-only inputs verified by hash (ADR-0026 section 3.1).

The backbone is restored from the P3 control's ``checkpoint-1024`` with the identity its own manifest records (``p3_checkpoint.restore``), extracted by ``p4_model.extract`` and its digest compared with the
digest ``results/p4-2026-11-12/<parent>-baseline/result.json`` recorded. NOT EXERCISED against the real files by the implementer (the files are in the main checkout's ``experiments/``).
"""

from pathlib import Path
from typing import Any

from arborlm.io import read_json

from . import core

P3_COMPACT = Path("results/p3-lt-2026-11-12")
P4_COMPACT = Path("results/p4-2026-11-12")


def parent_dir(parent: int) -> str:
    b, o = core.parent_ids(parent)
    return f"b{b}-o{o}"


def recorded_backbone_sha(repo: Path, parent: int) -> str:
    return str(read_json(repo / P4_COMPACT / f"{parent_dir(parent)}-baseline" / "result.json")["backbone_sha256"])


def consumed_ranks(repo: Path, parent: int) -> list[int]:
    """The ranks the P2/P3 lineage of this parent trained on: the ``ranked_train_row_ids`` of the parent's order record (the compact copy in ``results/``; rank interval [0, 2048])."""
    order = read_json(repo / P3_COMPACT / f"{parent_dir(parent)}-control" / "order.json")
    if order["rank_interval"] != [0, 2048]:
        raise ValueError("the parent's order is not over train ranks 0-2047")
    return [int(x) for x in order["ranked_train_row_ids"]]


def load_backbone(repo: Path, parent_suite: Path, parent: int) -> tuple[Any, str]:
    """Returns (Backbone, backbone digest). Raises if the digest differs from the P4 record."""
    from arborlm.engine import configure_cpu
    from arborlm.longer_training import _isolated_rng
    from arborlm.optimization_followup import _optimizer
    from arborlm.p2_config import CONTROL, Cell
    from arborlm.p2_model import FollowupModel
    from arborlm.p3_checkpoint import restore
    from arborlm.p4_model import backbone_digest, extract

    b, o = core.parent_ids(parent)
    compact = read_json(repo / P3_COMPACT / f"{parent_dir(parent)}-control" / "manifest.json")
    cell_dir = parent_suite / "cells" / compact["run_id"]
    identity = read_json(cell_dir / "manifest.json")["checkpoint_identity"]
    cell = Cell(b, 201, o, CONTROL)
    configure_cpu()
    with _isolated_rng():
        original = FollowupModel(cell)
        opt = _optimizer(original)
        done = restore(cell_dir / "checkpoint-1024", original, opt, identity)
        if done["completed_step"] != 1024 or not original.bypass:
            raise ValueError("the parent must be the final bypassed P3 control")
        backbone = extract(original)
    digest = backbone_digest(backbone)
    want = recorded_backbone_sha(repo, parent)
    if digest != want:
        raise ValueError(f"backbone digest differs from the P4 record for {parent_dir(parent)}")
    return backbone, digest


def checkpoint_files(repo: Path, parent_suite: Path) -> dict[str, str]:
    """SHA-256 of the nine parents' ``checkpoint-1024`` state and index files (frozen inputs, section 11 item 7): checked by every task (PAUSED — IDENTITY on a difference)."""
    from arborlm.io import file_sha256

    out: dict[str, str] = {}
    for p in range(9):
        run_id = read_json(repo / P3_COMPACT / f"{parent_dir(p)}-control" / "manifest.json")["run_id"]
        for name in ("state.pt", "index.json"):
            f = parent_suite / "cells" / run_id / "checkpoint-1024" / name
            out[str(f)] = file_sha256(f)
    return out
