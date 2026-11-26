# ruff: noqa: E501
"""P10IS6 parents (ADR-0031 section 7, addendum rulings 9 and 12): the adapter that runs the P2 control followed by the P3 continuation for backbone and order seeds outside the registered whitelists, with the identity gate on all nine old parents.

The recipe (P2 control, memory bypassed and frozen; P3 continuation to 1,024 updates) is the existing code's: ``p2_model.FollowupModel`` (or, for new parents, a subclass that does not construct the control memory), ``optimization_followup._optimizer`` and
``_training_step``, ``p4_model.extract`` and ``backbone_digest``. A duck-typed cell replaces ``p2_config.Cell`` (whose ``__post_init__`` accepts only the registered seeds); the order is ``randperm(2048)`` from a generator seeded with the order seed
(``p2_data.order_ids`` without its whitelist). Update ``s`` (1-based) takes rows ``[(s - 1) * 8 mod 2048, + 8)`` of the order-permuted ranks 0-2047: P2's ``(s - 1) * 8`` for s <= 256 and P3's ``batch_offset`` after.

CONTROL MEMORY (ruling 12, G9). The control memory ``Memory("learned_tree", 201)`` is NOT constructed for new parents. The identity gate runs the same path first (``control_memory=None``): if all nine old digests are reproduced bitwise the gate records ``control_memory: null``.
Only if that fails is the full old recipe tried with 201 constructed (a DECLARED RE-USE of seed 201, recorded in the gate result and printed in the report), and new parents then use whichever setting passed. No new parent is trained before an identity record shows nine
bitwise-equal digests (``train_new_parents`` refuses without it); an existing parent file is accepted only if the digest recomputed from its stored state equals the stored one, otherwise it is kept aside, the attempt is logged, and the parent is retrained.
NOT EXERCISED against the real files by the implementer (they live in the lead's checkout).
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


def _no_control_model_class() -> Any:
    from torch import nn

    from arborlm.model import Block, _Embedding
    from arborlm.p2_model import FollowupModel
    from arborlm.pilot_model import CONTEXT, VOCAB, WIDTH

    class NoControlModel(FollowupModel):
        """``FollowupModel`` for new parents: the same backbone draw and parameters, no control memory (a parameter-free stub holds its place for ``_training_step``'s control check)."""

        def __init__(self, cell: Any) -> None:
            nn.Module.__init__(self)
            self.cell = cell
            self.variant = "learned_tree"
            self.seed = cell.backbone
            with torch.random.fork_rng(devices=[]):
                torch.default_generator.manual_seed(cell.backbone)
                self.token = _Embedding(VOCAB, WIDTH)
                self.position = _Embedding(CONTEXT, WIDTH)
                self.blocks = nn.ModuleList([Block(64), Block(64)])
                self.final_norm = nn.LayerNorm(WIDTH, eps=1e-5)
            self.register_buffer("mask", torch.full((CONTEXT, CONTEXT), -torch.inf, dtype=torch.float32).triu(1), persistent=False)
            self.memory_state = nn.Module()
            self.bypass = True

    return NoControlModel


def order_permutation(order_seed: int) -> Tensor:
    return torch.randperm(TRAIN_SEEN, generator=torch.Generator(device="cpu").manual_seed(order_seed), device="cpu")


def untrained_backbone(backbone_seed: int) -> Any:
    """A backbone of the study's structure from any seed (tests: test-range seeds; the load template of ``stages.real_resources``)."""
    from arborlm.p4_model import extract

    return extract(_no_control_model_class()(AdapterCell(backbone_seed, 0, 0)))


def train_backbone(backbone_seed: int, order_seed: int, train_rows: Tensor, *, steps: int, control_memory: int | None) -> tuple[Any, str]:
    """The control recipe to ``steps`` updates (1,024 in the registered use). ``train_rows`` is the [>=2048, 65] int64 tensor of train ranks 0-2047 first. ``control_memory`` None: not constructed (new parents, ruling 12); 201: the old recipe's
    declared re-use. Returns (Backbone, digest). The process must have been configured (``engine.configure_cpu``)."""
    from arborlm.longer_training import _isolated_rng
    from arborlm.optimization_followup import _optimizer, _training_step
    from arborlm.p2_model import FollowupModel
    from arborlm.p4_model import backbone_digest, extract

    if train_rows.shape[0] < TRAIN_SEEN or train_rows.shape[1] != 65:
        raise core.EngineeringStop("ENGINEERING STOP — the parent recipe needs the 2,048 train rows of ranks 0-2047")
    ordered = train_rows[:TRAIN_SEEN][order_permutation(order_seed)]
    with _isolated_rng():
        if control_memory is None:
            model = _no_control_model_class()(AdapterCell(backbone_seed, 0, order_seed))
        else:
            model = FollowupModel(AdapterCell(backbone_seed, control_memory, order_seed))  # type: ignore[arg-type]
        opt = _optimizer(model)
        stored = sum(p.numel() for p in model.parameters())
        trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
        if stored != (27392 if control_memory is None else 225793) or trainable != 27392:
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


def _gate_once(repo: Path, train_rows: Tensor, n: int, control: int | None, recorded: Mapping[int, str] | None) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for p in range(9):
        b, o = core.old_parent_ids(p)
        _, digest = train_backbone(b, o, train_rows, steps=n, control_memory=control)
        want = (recorded or {}).get(p) or recorded_digest(repo, p)
        out[f"b{b}-o{o}"] = {"digest": digest, "recorded": want, "same": digest == want}
    return out


def identity_gate(repo: Path, train_rows: Tensor, cfg: Mapping[str, Any], *, steps: int | None = None, recorded: Mapping[int, str] | None = None) -> dict[str, Any]:
    """All nine old parents (G10): the adapter, from each parent's recorded backbone and order seeds, must give that parent's recorded backbone digest bitwise. The new-parent path (no control memory) is tried first; only if it fails is the old recipe
    with 201 constructed tried, as a declared re-use. ``steps`` and ``recorded`` are test hooks (the registered use: 1,024 and the P4 records)."""
    n = steps if steps is not None else int(cfg["ladder"]["parent_updates"])
    reuse = int(cfg["seeds"]["control_memory_reuse"])
    attempts = [("not constructed", None, _gate_once(repo, train_rows, n, None, recorded))]
    if not all(v["same"] for v in attempts[0][2].values()):
        attempts.append((f"constructed with {reuse} (declared re-use)", reuse, _gate_once(repo, train_rows, n, reuse, recorded)))
    name, control, parents_ = next(((nm, c, d) for nm, c, d in attempts if all(v["same"] for v in d.values())), attempts[-1])
    passed = all(v["same"] for v in parents_.values()) and len(parents_) == 9
    return {"name": "adapter_identity", "passed": passed, "parents": parents_, "control_memory": control if passed else None, "control_memory_note": name, "declared_reuse": {"control_memory_seed": reuse} if control is not None else None, "attempts": [{"path": nm, "all_nine_equal": all(v["same"] for v in d.values())} for nm, _, d in attempts]}


def require_identity(identity: Mapping[str, Any] | None) -> int | None:
    """The condition of P0: an ``adapter_identity`` record with ``passed: true`` and nine bitwise-equal digests. Returns the control-memory setting that passed (None: not constructed)."""
    if not identity or identity.get("passed") is not True or len(identity.get("parents", {})) != 9 or not all(v.get("digest") == v.get("recorded") and v.get("same") is True for v in identity["parents"].values()):
        raise core.EngineeringStop("ENGINEERING STOP — no new parent is trained before an adapter identity record shows nine bitwise-equal digests for the nine old parents")
    c = identity.get("control_memory")
    return None if c is None else int(c)


def load_new_backbone(path: Path, template: Any) -> Any:
    """A trained new backbone from its file (the template is a ``Backbone`` of the same structure; the caller deep-copies per use)."""
    state = torch.load(path, weights_only=True, map_location="cpu")
    bb = copy.deepcopy(template)
    bb.load_state_dict(state["backbone"])
    return bb


def train_new_parents(cfg: Mapping[str, Any], train_rows: Tensor, out_dir: Path, *, group: str, identity: Mapping[str, Any] | None, steps: int | None = None) -> dict[str, Any]:
    """P0: ``group`` is ``registered`` (nine parents) or ``calibration`` (three). Refuses without the identity record. An existing file is accepted only if the digest recomputed from its stored state equals the stored digest; otherwise it is kept aside
    (``<name>.aside-N``), the attempt logged under ``attempts/``, and the parent retrained."""
    from arborlm.io import write_json
    from arborlm.p4_model import backbone_digest

    control = require_identity(identity)
    n = steps if steps is not None else int(cfg["ladder"]["parent_updates"])
    count = 9 if group == "registered" else 3
    out_dir.mkdir(parents=True, exist_ok=True)
    template = untrained_backbone(core.test_seed(799, cfg))
    rec: dict[str, Any] = {}
    for p in range(count):
        bs, os_ = core.backbone_seed(cfg, group, p), core.order_seed(cfg, group, p)
        path = out_dir / f"{group}{p:02d}.pt"
        if path.exists():
            state = torch.load(path, weights_only=True, map_location="cpu")
            try:
                recomputed = backbone_digest(load_new_backbone(path, template))
            except Exception:  # noqa: BLE001 - a corrupt or mismatched file is kept aside below
                recomputed = None
            if recomputed is not None and recomputed == state.get("digest") and state.get("backbone_seed") == bs and state.get("order_seed") == os_ and state.get("steps") == n:
                rec[f"{group}{p:02d}"] = {"digest": recomputed, "backbone_seed": bs, "order_seed": os_, "reused_file": True, "digest_recomputed": True}
                continue
            k = len(list(out_dir.glob(f"{path.name}.aside-*")))
            path.rename(out_dir / f"{path.name}.aside-{k}")
            core.log_attempt(out_dir, "parent file kept aside: recomputed digest differs from the stored one", file=path.name, aside=k)
        bb, digest = train_backbone(bs, os_, train_rows, steps=n, control_memory=control)
        torch.save({"backbone": bb.state_dict(), "digest": digest, "backbone_seed": bs, "order_seed": os_, "steps": n}, path)
        rec[f"{group}{p:02d}"] = {"digest": digest, "backbone_seed": bs, "order_seed": os_, "reused_file": False, "digest_recomputed": True}
    write_json(out_dir / f"{group}_parents.json", rec)
    return rec
