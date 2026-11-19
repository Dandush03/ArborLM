# ruff: noqa: E501
"""P10IS6 parents (ADR-0031 section 7): the adapter that runs the P2 control followed by the P3 continuation for backbone and order seeds outside the registered whitelists, with the identity gate on all nine old parents.

The recipe (P2 control, memory bypassed and frozen; P3 continuation to 1,024 updates) is the existing code's: ``p2_model.FollowupModel``, ``optimization_followup._optimizer`` and ``_training_step``, ``p4_model.extract`` and
``backbone_digest``. A duck-typed cell replaces ``p2_config.Cell`` (whose ``__post_init__`` accepts only the registered seeds); the order is ``randperm(2048)`` from a generator seeded with the order seed (``p2_data.order_ids`` without its
whitelist). Update ``s`` (1-based) takes rows ``[(s - 1) * 8 mod 2048, + 8)`` of the order-permuted ranks 0-2047: for s <= 256 this is P2's ``(s - 1) * 8`` and for s > 256 P3's ``batch_offset``. The control memory
(``Memory("learned_tree", 201)``) is constructed after the backbone as in the old recipe and never trained: 201 is a DECLARED RE-USE (ruling G9). The identity gate (ruling G10) must reproduce all nine old parents' recorded backbone digests
bitwise on the platform of record before any new parent is trained. NOT EXERCISED against the real files by the implementer (they live in the lead's checkout).
"""

import copy
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch
from torch import Tensor

from arborlm.io import read_json

from . import core

P4_COMPACT = Path("results/p4-2026-11-12")
CONTROL = "disabled_throughout"
TRAIN_SEEN = 2048
BATCH = 8


@dataclass(frozen=True)
class AdapterCell:
    backbone: int
    memory: int
    order: int
    condition: str = CONTROL


def order_permutation(order_seed: int) -> Tensor:
    return torch.randperm(TRAIN_SEEN, generator=torch.Generator(device="cpu").manual_seed(order_seed), device="cpu")


def train_backbone(backbone_seed: int, order_seed: int, train_rows: Tensor, *, steps: int, control_memory: int) -> tuple[Any, str]:
    """The control recipe to ``steps`` updates (1,024 in the registered use). ``train_rows`` is the [>=2048, 65] int64 tensor of train ranks 0-2047 first. Returns (Backbone, digest). The process must have been configured (``engine.configure_cpu``)."""
    from arborlm.longer_training import _isolated_rng
    from arborlm.optimization_followup import _optimizer, _training_step
    from arborlm.p2_model import FollowupModel
    from arborlm.p4_model import backbone_digest, extract

    if train_rows.shape[0] < TRAIN_SEEN or train_rows.shape[1] != 65:
        raise core.EngineeringStop("ENGINEERING STOP — the parent recipe needs the 2,048 train rows of ranks 0-2047")
    ordered = train_rows[:TRAIN_SEEN][order_permutation(order_seed)]
    with _isolated_rng():
        model = FollowupModel(AdapterCell(backbone_seed, control_memory, order_seed))  # type: ignore[arg-type]
        opt = _optimizer(model)
        stored = sum(p.numel() for p in model.parameters())
        trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
        if stored != 225793 or trainable != 27392:
            raise core.EngineeringStop("ENGINEERING STOP — the parent's stored or trainable parameter count differs from the recipe's")
        for step in range(1, steps + 1):
            off = ((step - 1) * BATCH) % TRAIN_SEEN
            _training_step(model, opt, ordered[off : off + BATCH], step)
        bb = extract(model)
        digest = backbone_digest(bb)
    return bb, digest


def recorded_digest(repo: Path, p: int) -> str:
    b, o = core.old_parent_ids(p)
    return str(read_json(repo / P4_COMPACT / f"b{b}-o{o}-baseline" / "result.json")["backbone_sha256"])


def identity_gate(repo: Path, train_rows: Tensor, cfg: Mapping[str, Any], *, steps: int | None = None, recorded: Mapping[int, str] | None = None) -> dict[str, Any]:
    """All nine old parents (G10): the adapter, from each parent's recorded backbone and order seeds, must give that parent's recorded backbone digest bitwise. ``steps`` and ``recorded`` are test hooks (the registered use: 1,024 and the P4 records)."""
    n = steps if steps is not None else int(cfg["ladder"]["parent_updates"])
    out: dict[str, Any] = {}
    for p in range(9):
        b, o = core.old_parent_ids(p)
        _, digest = train_backbone(b, o, train_rows, steps=n, control_memory=int(cfg["seeds"]["control_memory_reuse"]))
        want = (recorded or {}).get(p) or recorded_digest(repo, p)
        out[f"b{b}-o{o}"] = {"digest": digest, "recorded": want, "same": digest == want}
    return {"name": "adapter_identity", "passed": all(v["same"] for v in out.values()), "parents": out, "declared_reuse": {"control_memory_seed": int(cfg["seeds"]["control_memory_reuse"])}}


def train_new_parents(cfg: Mapping[str, Any], train_rows: Tensor, out_dir: Path, *, group: str, steps: int | None = None) -> dict[str, Any]:
    """P0: ``group`` is ``registered`` (nine parents) or ``calibration`` (three). Each backbone is saved as its state dict plus its digest; a file that exists is verified, not retrained."""
    from arborlm.io import write_json

    n = steps if steps is not None else int(cfg["ladder"]["parent_updates"])
    count = 9 if group == "registered" else 3
    out_dir.mkdir(parents=True, exist_ok=True)
    rec: dict[str, Any] = {}
    for p in range(count):
        bs, os_ = core.backbone_seed(cfg, group, p), core.order_seed(cfg, group, p)
        path = out_dir / f"{group}{p:02d}.pt"
        if path.exists():
            state = torch.load(path, weights_only=True, map_location="cpu")
            rec[f"{group}{p:02d}"] = {"digest": state["digest"], "backbone_seed": bs, "order_seed": os_, "reused_file": True}
            continue
        bb, digest = train_backbone(bs, os_, train_rows, steps=n, control_memory=int(cfg["seeds"]["control_memory_reuse"]))
        torch.save({"backbone": bb.state_dict(), "digest": digest, "backbone_seed": bs, "order_seed": os_, "steps": n}, path)
        rec[f"{group}{p:02d}"] = {"digest": digest, "backbone_seed": bs, "order_seed": os_, "reused_file": False}
    write_json(out_dir / f"{group}_parents.json", rec)
    return rec


def load_new_backbone(path: Path, template: Any) -> Any:
    """A trained new backbone from its file (the template is a ``Backbone`` of the same structure; the caller deep-copies per use)."""
    state = torch.load(path, weights_only=True, map_location="cpu")
    bb = copy.deepcopy(template)
    bb.load_state_dict(state["backbone"])
    return bb
