# ruff: noqa: E501
"""Part T's arms: world, seed plan, training of every cell, snapshots (ADR-0025 sections 5.1, 5.2, 7, 11 item 4, 19).

Re-uses P10-S2's code unedited: the student and LoRA adapter (``model``), the sparse store, the oracle code book, the table arm (``memory``), the loss, collation and batch plan (``train``), the example bank
and snapshot files (``world``), and the data container (``worldio``). New here: this study's seed plan (``SeedPlanT``: every generator through ``core.seeded_generator`` with the listed seeds), the world built from
Part Q's bundle with Part Q's training draws, the dense append arm (``AppendLoRAArm``), and one training loop with a checkpoint every 500 updates (optimizer included), resume, and the non-finite stop that is NOT
resumed (ruling L4, correction C2). Device: the frozen training device is MPS and scoring is CPU, as P10-S2 selected them (``train.select_device`` never chooses by availability); tests run on CPU.
"""

import copy
import dataclasses
import math
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch
from torch import nn

from studies.p10s2 import train as p10train
from studies.p10s2.data import TrainItem
from studies.p10s2.memory import (
    Arm,
    CodeBook,
    LoRAArm,
    MemoryArm,
    SparseStore,
    TableArm,
    new_lora_arm,
)
from studies.p10s2.model import LoRAAdapter
from studies.p10s2.routing import RouterSpec
from studies.p10s2.tokenization import Example
from studies.p10s2.world import World, load_arm, save_arm
from studies.p10s2.worldio import DataBundle, RunConfig, build_world

from .common import core

ROLE = {"stage-1 store": 0, "appended rows": 1, "M-joint store": 2, "D1": 3, "second adapter of D-append": 4, "D-joint": 5, "E-table": 6, "router projection and keys": 7}


class SeedPlanT:
    """The seeds of one replicate, calibration draw or rehearsal draw (section 6). ``gen(offset, purpose)`` serves the reused P10-S2 code by its offsets: 2 batch order (+2), 4 permutation controls (+4),
    3 router (the purpose says which: "router initialization" is initialization role 7, "router sampling" the +13 stream), 10 the code hash (+10), 1 the training draw (+1). ``init(role)`` is the initialization
    generator of a role j. Any other offset is refused."""

    def __init__(self, cfg: Mapping[str, Any], mode: str, index: int, extra_allowed: Sequence[int] = ()) -> None:
        self.cfg, self.mode, self.index = cfg, mode, index
        self.values = core.partt_replicate_values(cfg, mode, index)
        self.allowed = core.partt_listed_seeds(cfg, mode) | frozenset(extra_allowed) | (core.test_range(cfg) if mode == "test" else frozenset())

    @property
    def base(self) -> int:
        return int(self.values["base"])

    def init_seed(self, role: str) -> int:
        return int(self.values["init"][role])

    def init(self, role: str) -> torch.Generator:
        return core.seeded_generator(self.init_seed(role), f"initialization: {role}", self.allowed)

    def gen(self, offset: int, purpose: str | None = None) -> torch.Generator:
        d = self.values["data"]
        if offset == 2:
            seed = d["batch_order"]
        elif offset == 4:
            seed = d["permutation_controls"]
        elif offset == 1:
            seed = d["training_draw"]
        elif offset == 3:
            seed = self.init_seed("router projection and keys") if purpose == "router initialization" else d["router"]
        else:
            raise core.SeedRefused(f"P10-S2 offset {offset} is not served by this study's seed plan: use init(role)")
        return core.seeded_generator(int(seed), purpose or f"offset {offset}", self.allowed)

    def route_pieces_gen(self) -> torch.Generator:
        """The generator that draws the 200 WikiText-2 train pieces of the route accuracy on general text: the listed seed 250918 in a registered run; in any other mode the replicate's router stream (250918 is a registered-mode seed)."""
        seed = int(self.values["route_pieces"])
        return core.seeded_generator(seed, "route accuracy pieces", self.allowed | {seed})

    def code_seed(self) -> int:
        return int(self.values["data"]["code_hash"])


@dataclass
class Streams:
    """What P10-S2's ``World.train_examples`` reads: ``t[capability]``, the replicate's training draw (teacher output only; no gold)."""

    t: dict[str, list[TrainItem]]
    gold: dict[str, list[TrainItem]]
    shared_sources: int = 0
    exclusive: dict[str, int] = dataclasses.field(default_factory=dict)
    half: int = 0


class WorldT(World):
    """P10-S2's ``World`` with this study's seed plan and training draws."""

    cfg_t: Mapping[str, Any]
    plan_mode: str = "registered"
    extra_seeds: tuple[int, ...] = ()
    plan_offset: int = 0  # a repeated calibration: stream position 0 and 1 take the seeds of calibration draws 2 and 3 (section 7.1 rule 4)

    def plan(self, r: int) -> SeedPlanT:  # type: ignore[override]
        return SeedPlanT(self.cfg_t, self.plan_mode, r + self.plan_offset, self.extra_seeds)

    def codes(self, r: int) -> CodeBook:
        return CodeBook(self.plan(r).code_seed(), self.vocabulary)


def run_config(cfg: Mapping[str, Any], *, layer: int, updates: int, store_rate: float, lora_rate: float, device: str, batch: int | None = None, rows: int | None = None, router: RouterSpec | None = None, decision_token: int = 64, window_tokens: int = 256, ranks: tuple[int, int] | None = None, replay: int | None = None) -> RunConfig:
    m, t = cfg["memory"], cfg["training"]
    return RunConfig(layer, updates, batch or t["batch"], replay if replay is not None else m["replay_rows"], rows or m["rows_per_stage"], store_rate, lora_rate, (ranks or (m["lora_rank_single"], m["lora_rank_joint"]))[0], (ranks or (m["lora_rank_single"], m["lora_rank_joint"]))[1], router or RouterSpec(500, 64, 0.001, 8000, 4000, 64), decision_token, window_tokens, device)


def build_world_t(bundle: DataBundle, cfg: Mapping[str, Any], draws: Sequence[Mapping[str, Sequence[TrainItem]]], run: RunConfig, *, plan_mode: str, extra_seeds: Sequence[int] = ()) -> WorldT:
    """The world from Part Q's bundle (the frozen data files) with the replicates' training draws. ``build_world`` is called with no replicate (its own draws use P10-S2's seeds and are not used)."""
    w0 = build_world(bundle, "test", 0, run)
    w = WorldT(**{f.name: getattr(w0, f.name) for f in dataclasses.fields(w0)})
    w.cfg_t, w.plan_mode, w.extra_seeds = cfg, plan_mode, tuple(extra_seeds)
    w.streams = [Streams({c: list(d[c]) for c in core.TASKS}, {c: [] for c in core.TASKS}) for d in draws]  # type: ignore[assignment]
    w.replicates = len(draws)
    n_seen = 300
    w.seen_items = [{c: [x for x in s.t[c]][:n_seen] for c in core.TASKS} for s in w.streams]  # type: ignore[attr-defined]
    return w


# --- the dense append arm ----------------------------------------------------------------------------------------------------------------------------
class SumAdapter:
    """Both adapters applied on every task prompt: the sum of their deltas (D-append, section 5.2)."""

    def __init__(self, first: LoRAAdapter, second: LoRAAdapter) -> None:
        self.first, self.second = first, second

    def delta(self, block: int, which: str, h: torch.Tensor) -> torch.Tensor:
        return self.first.delta(block, which, h) + self.second.delta(block, which, h)


class AppendLoRAArm(Arm):
    """D-append: the first rank-42 adapter frozen, a second rank-42 adapter trainable, both applied on every task prompt (route "none": neither)."""

    kind = "lora"

    def __init__(self, first: LoRAAdapter, second: LoRAAdapter) -> None:
        self.first, self.second = first, second
        for p in first.parameters():
            p.requires_grad_(False)

    def trainable(self) -> list[nn.Parameter]:
        return [p for p in self.second.parameters() if p.requires_grad]

    def to(self, device: torch.device) -> None:
        self.first.to(device)
        self.second.to(device)

    def parameter_count(self) -> int:
        return sum(p.numel() for p in [*self.first.parameters(), *self.second.parameters()])

    def state_hash(self) -> str:
        from arborlm.io import sha256
        from studies.p10s2.model import tensor_sha

        return sha256("|".join(tensor_sha(p) for p in [*self.first.parameters(), *self.second.parameters()]).encode())

    def prepare(self, reads: Sequence[Sequence[Any]], batch: int, length: int, device: torch.device, ablation: Any = None) -> tuple[torch.Tensor | None, Any]:
        if not any(reads):
            return None, None
        return None, SumAdapter(self.first, self.second)


def save_t(arm: Arm, directory: Path, name: str) -> dict[str, Any]:
    """Snapshot of any arm of this study (the P10-S2 kinds through ``save_arm``; the append arm as two adapters)."""
    if isinstance(arm, AppendLoRAArm):
        import json

        from arborlm.io import atomic_write, file_sha256

        directory.mkdir(parents=True, exist_ok=True)
        safe = name.replace("/", "__").replace("@", "_at_")
        data, manifest = directory / f"{safe}.pt", directory / f"{safe}.manifest.json"
        if data.exists():
            raise FileExistsError(f"snapshot {name!r} exists and is immutable")
        torch.save({"kind": "lora2", "rank": arm.first.rank, "first": {k: v.detach().clone() for k, v in arm.first.state_dict().items()}, "second": {k: v.detach().clone() for k, v in arm.second.state_dict().items()}}, data)
        m = {"name": name, "kind": "lora2", "file": data.name, "file_sha256": file_sha256(data), "arm_hash": arm.state_hash()}
        atomic_write(manifest, (json.dumps(m, sort_keys=True) + "\n").encode())
        return m
    return save_arm(arm, directory, name)


def load_t(world: WorldT, r: int, directory: Path, name: str) -> Arm:
    import json

    from arborlm.io import file_sha256

    safe = name.replace("/", "__").replace("@", "_at_")
    data, manifest = directory / f"{safe}.pt", directory / f"{safe}.manifest.json"
    m = json.loads(manifest.read_text())
    if m["kind"] == "lora2":
        if file_sha256(data) != m["file_sha256"]:
            raise ValueError(f"snapshot {name!r} does not hash to its manifest")
        st = torch.load(data, weights_only=True)
        a, b = LoRAAdapter(world.cfg, st["rank"], None), LoRAAdapter(world.cfg, st["rank"], None)
        a.load_state_dict(st["first"])
        b.load_state_dict(st["second"])
        arm = AppendLoRAArm(a, b)
        for p in arm.second.parameters():
            p.requires_grad_(False)
        if arm.state_hash() != m["arm_hash"]:
            raise ValueError(f"snapshot {name!r} arm hash differs after loading")
        return arm
    return load_arm(world, r, directory, name)  # type: ignore[arg-type]


# --- cells ------------------------------------------------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class CellSpec:
    arm: str
    order: str  # "AB", "BA" or "-"
    rep: int
    capability: str = ""  # E-table only

    @property
    def label(self) -> str:
        return f"r{self.rep}/{self.arm}/{self.order if not self.capability else self.capability}"

    @property
    def parent(self) -> "CellSpec | None":
        p = {"M-append": "M1", "M-seq": "M1", "D-append": "D1", "D-seq": "D1"}.get(self.arm)
        if self.arm == "M-ii":
            p = "M-append"
        return None if p is None else CellSpec(p, self.order, self.rep)


def build_cell_arm(world: WorldT, spec: CellSpec, parent: Arm | None) -> tuple[Arm, list[Example], dict[str, Any]]:
    """The untrained arm of a cell, its training rows and the training options (updates multiplier, replay). The initialization generators are the role seeds of section 6."""
    plan = world.plan(spec.rep)
    width, n = world.cfg.width, world.rows_per_stage
    f, s = (spec.order[0], spec.order[1]) if spec.order != "-" else ("", "")
    codes = world.codes(spec.rep)
    opts: dict[str, Any] = {"updates_x": 1, "rate": world.store_lr}
    a = spec.arm
    arm: Arm
    if a == "M1":
        arm, rows = MemoryArm(SparseStore.new(width, n, plan.init("stage-1 store")), world.layer, codes), world.train_examples(spec.rep, f)
    elif a == "M-append":
        assert isinstance(parent, MemoryArm)
        store = parent.store.clone()
        store.append_stage(n, plan.init("appended rows"))
        store.freeze_stage(0)
        store.set_trainable([1])
        arm, rows = MemoryArm(store, world.layer, codes), world.train_examples(spec.rep, s)
    elif a == "M-seq":
        assert isinstance(parent, MemoryArm)
        store = parent.store.clone()
        store.set_trainable([0])
        arm, rows = MemoryArm(store, world.layer, codes), world.train_examples(spec.rep, s)
    elif a == "M-ii":
        assert isinstance(parent, MemoryArm)
        store = parent.store.clone()
        store.set_trainable([0, 1])
        arm, rows = MemoryArm(store, world.layer, codes), world.train_examples(spec.rep, s)
        opts |= {"replay": world.train_examples(spec.rep, f), "replay_rows": world.replay_rows}
    elif a == "D1":
        arm, rows = new_lora_arm(world.cfg, world.rank_single, plan.init("D1")), world.train_examples(spec.rep, f)
        opts["rate"] = world.lora_lr
    elif a == "D-append":
        assert isinstance(parent, LoRAArm)
        arm = AppendLoRAArm(copy.deepcopy(parent.adapter), LoRAAdapter(world.cfg, world.rank_single, plan.init("second adapter of D-append")))
        rows, opts["rate"] = world.train_examples(spec.rep, s), world.lora_lr
    elif a == "D-seq":
        assert isinstance(parent, LoRAArm)
        arm, rows = copy.deepcopy(parent), world.train_examples(spec.rep, s)
        opts["rate"] = world.lora_lr
    elif a == "M-joint":
        arm = MemoryArm(SparseStore.new(width, 2 * n, plan.init("M-joint store")), world.layer, codes)
        rows, opts["updates_x"] = [*world.train_examples(spec.rep, "A"), *world.train_examples(spec.rep, "B")], 2
    elif a == "D-joint":
        arm = new_lora_arm(world.cfg, world.rank_joint, plan.init("D-joint"))
        rows, opts["updates_x"], opts["rate"] = [*world.train_examples(spec.rep, "A"), *world.train_examples(spec.rep, "B")], 2, world.lora_lr
    elif a == "E-table":
        arm, rows = TableArm(spec.capability, width, world.vocabulary, world.layer, plan.init("E-table")), world.train_examples(spec.rep, spec.capability)
        opts["rate"] = getattr(world, "etable_lr", world.store_lr)
    else:
        raise ValueError(f"unknown arm {a!r}")
    return arm, rows, opts


# --- training with checkpoints ----------------------------------------------------------------------------------------------------------------------------
def train_cell(world: WorldT, spec: CellSpec, arm: Arm, rows: Sequence[Example], opts: Mapping[str, Any], updates: int, *, checkpoint_dir: Path | None = None, checkpoint_every: int = 500, stop_after: int | None = None, snapshots: Sequence[int] = (), on_snapshot: Any = None, record_losses: int = 0) -> dict[str, Any]:
    """U updates of batch 32 with AdamW (no weight decay, clip 1.0, constant rate, fresh optimizer state), as P10-S2's ``train_arm``. A checkpoint (trainable parameters and the optimizer's state) every
    ``checkpoint_every`` updates; a call with an existing checkpoint RESUMES from it and the record says so. A non-finite loss ends the cell as ``STOPPED_NONFINITE`` with the last finite checkpoint named
    and the cell is never resumed (the caller reads ``partt_plan.resume_decision``). ``stop_after`` ends the call early, as a cap stop would (the rehearsal's forced pause). Returns the record."""
    plan = world.plan(spec.rep)
    dev = world.device
    params = arm.trainable()
    if not params:
        raise ValueError("the arm has no trainable parameter")
    clip = float(world.cfg_t["training"]["clip_norm"])
    losses: list[float] = []
    start, resumed = 0, False
    ck_path = None if checkpoint_dir is None else checkpoint_dir / f"{spec.label.replace('/', '__')}.ckpt"
    t0 = time.perf_counter()
    if dev.type == "mps":
        p10train.MPS_IN_USE = True
    batches = p10train.batch_plan(len(rows), updates, world.batch, plan.gen(2, "batch order"))
    replay = opts.get("replay")
    rplan = p10train.batch_plan(len(replay), updates, int(opts["replay_rows"]), plan.gen(2, "M-ii replayed rows order")) if replay is not None else None
    status, err, last_ck = "COMPLETE", "", None
    try:
        world.student.to(dev)
        arm.to(dev)
        opt = torch.optim.AdamW(params, lr=float(opts["rate"]), weight_decay=float(world.cfg_t["training"]["weight_decay"]))
        if ck_path is not None and ck_path.is_file():
            ck = torch.load(ck_path, weights_only=False, map_location=dev)
            for p, v in zip(params, ck["params"], strict=True):
                p.data.copy_(v)
            opt.load_state_dict(ck["opt"])
            start, resumed, losses, last_ck = int(ck["update"]), True, list(ck["losses"]), ck["update"]
        for u in range(start, updates):
            if stop_after is not None and u - start >= stop_after:
                status, err = "PAUSED", f"stopped after {stop_after} updates (cap or forced pause)"
                break
            examples = [rows[i] for i in batches[u]] + ([replay[i] for i in rplan[u]] if rplan is not None and replay is not None else [])
            loss = p10train.loss_of(world.student, arm, examples, world.marker_index, dev)
            if not torch.isfinite(loss):
                status, err = "STOPPED_NONFINITE", f"non-finite loss at update {u}"
                break
            opt.zero_grad(set_to_none=True)
            loss.backward()  # type: ignore[no-untyped-call]
            torch.nn.utils.clip_grad_norm_(params, clip)
            opt.step()
            losses.append(float(loss.item()))
            if on_snapshot is not None and (u + 1) in snapshots:  # a ladder snapshot: scored on CPU while the training state is kept
                arm.to(torch.device("cpu"))
                world.student.to(torch.device("cpu"))
                on_snapshot(u + 1, arm)
                arm.to(dev)
                world.student.to(dev)
            if ck_path is not None and (u + 1) % checkpoint_every == 0 and u + 1 < updates:
                ck_path.parent.mkdir(parents=True, exist_ok=True)
                torch.save({"update": u + 1, "params": [p.detach().cpu().clone() for p in params], "opt": opt.state_dict(), "losses": losses}, ck_path)
                last_ck = u + 1
        if status == "PAUSED" and ck_path is not None:
            ck_path.parent.mkdir(parents=True, exist_ok=True)
            torch.save({"update": start + (stop_after or 0), "params": [p.detach().cpu().clone() for p in params], "opt": opt.state_dict(), "losses": losses}, ck_path)
            last_ck = start + (stop_after or 0)
    except Exception as e:  # noqa: BLE001 - a code or environment error is a recorded ERROR with its cause; the caller resumes it from the checkpoint once the cause is recorded (section 8.6)
        status, err = "ERROR", f"{type(e).__name__}: {e}"
    finally:
        wall = time.perf_counter() - t0
        arm.to(torch.device("cpu"))
        world.student.to(torch.device("cpu"))
    if status == "COMPLETE" and ck_path is not None and ck_path.exists():
        ck_path.unlink()  # resume checkpoints are deleted once the final snapshot is recorded (G20)
    done = len(losses)
    return {
        "label": spec.label, "status": status, "updates": updates, "updates_done": done, "resumed": resumed, "device": str(dev), "wall_seconds": wall, "seconds_per_update": wall / max(1, done - (start if resumed else 0)),
        "trainable_parameters": sum(p.numel() for p in params), "first_loss": losses[0] if losses else math.nan, "last_loss": losses[-1] if losses else math.nan, "last_finite_checkpoint": last_ck, "error": err,
        "cause_recorded": status == "ERROR", "losses_head": losses[:record_losses],
    }  # fmt: skip


def run_cell(world: WorldT, spec: CellSpec, updates: int, snap_dir: Path, ckpt_dir: Path | None, *, parent_arm: Arm | None = None, stop_after: int | None = None) -> tuple[dict[str, Any], Arm]:
    """One cell end to end: parent from its snapshot (unless given), build, train, snapshot. The append point of M-append is snapshotted before any update (APPEND COST)."""
    if spec.parent is not None and parent_arm is None:
        parent_arm = load_t(world, spec.rep, snap_dir, spec.parent.label)
    arm, rows, opts = build_cell_arm(world, spec, parent_arm)
    rec_extra: dict[str, Any] = {}
    if spec.arm == "M-append":
        rec_extra["append_snapshot"] = save_t(arm, snap_dir, f"{spec.label}@append") if not (snap_dir / (f"{spec.label}@append".replace("/", "__").replace("@", "_at_") + ".pt")).exists() else "exists"
    rec = train_cell(world, spec, arm, rows, opts, updates * int(opts["updates_x"]), checkpoint_dir=ckpt_dir, stop_after=stop_after)
    rec.update(rec_extra)
    if rec["status"] == "COMPLETE":
        rec["snapshot"] = save_t(arm, snap_dir, spec.label)
    return rec, arm


def frozen_unchanged(before: Mapping[str, str], arm: Arm) -> bool:
    """Gate G7 helper: the hashes of the frozen parts recorded before training equal those after."""
    return before == frozen_hashes(arm)


def frozen_hashes(arm: Arm) -> dict[str, str]:
    from studies.p10s2.model import tensor_sha

    out: dict[str, str] = {}
    if isinstance(arm, MemoryArm):
        for k in range(arm.store.stages):
            if not arm.store.keys[k].requires_grad:
                out[f"stage{k}"] = "|".join(tensor_sha(p) for p in arm.store.stage_parameters(k))
    if isinstance(arm, AppendLoRAArm):
        out["first_adapter"] = "|".join(tensor_sha(p) for p in arm.first.parameters())
    return out
