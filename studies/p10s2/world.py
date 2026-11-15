# ruff: noqa: E501
"""The contract between the data-generation step and the registered path: ``ExampleBank`` (stored tokenization records), ``World`` (everything a replicate needs) and the snapshot files.

The registered path never encodes text. The bank maps (task, English source, target) to an ``Example`` rebuilt from stored segment ids. A ``World`` is built either from the frozen data files of the
real data-generation step (not done here) or from the synthetic stand-ins (``dry``); every later step takes a ``World`` and adds no scientific code.
"""

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import torch

from arborlm.io import atomic_write, file_sha256, sha256

from . import core
from .data import Partition, Sizes, Streams, TrainItem
from .evaluate import EvalContext, PanelData
from .memory import Arm, CodeBook, LoRAArm, MemoryArm, SparseStore, TableArm, VersionStore
from .model import LoRAAdapter, Student, StudentConfig
from .routing import RouterSpec
from .tokenization import Example, ReferenceTokenizer, build_example, example_from_json


def example_key(task: str, en: str, target: str | None) -> str:
    return f"{task}|{sha256(en.encode())[:16]}|{sha256((target or '').encode())[:16]}"


class ExampleBank:
    """Examples keyed by (task, source, target). Prompts have no target."""

    def __init__(self, examples: Mapping[str, Example] | None = None) -> None:
        self.examples: dict[str, Example] = dict(examples or {})

    def add(self, task: str, en: str, target: str | None, ex: Example) -> None:
        self.examples[example_key(task, en, target)] = ex

    def prompt(self, task: str, en: str) -> Example:
        return self.examples[example_key(task, en, None)]

    def train(self, task: str, item: TrainItem) -> Example:
        return self.examples[example_key(task, item.en, item.target)]

    def build_from_tokenizer(self, tok: ReferenceTokenizer, vocab_index: Mapping[str, int], task: str, en: str, target: str | None) -> Example:
        k = example_key(task, en, target)
        if k not in self.examples:
            self.examples[k] = build_example(tok, task, en, target, vocab_index, k)
        return self.examples[k]

    def to_records(self) -> list[dict[str, Any]]:
        return [self.examples[k].to_json() for k in sorted(self.examples)]

    @staticmethod
    def from_records(records: Sequence[Mapping[str, Any]], vocab_index: Mapping[str, int]) -> "ExampleBank":
        b = ExampleBank()
        for r in records:
            b.examples[str(r["key"])] = example_from_json(r, vocab_index)
        return b


@dataclass
class World:
    cfg: StudentConfig
    student: Student
    decoder: Any
    mode: str
    replicates: int
    sizes: Sizes
    layer: int
    updates: int
    batch: int
    replay_rows: int
    rows_per_stage: int
    store_lr: float
    lora_lr: float
    rank_single: int
    rank_joint: int
    vocabulary: int
    bank: ExampleBank
    partition: Partition
    streams: list[Streams]
    ctx: EvalContext
    d_con: dict[str, PanelData]
    d_cal: dict[str, PanelData]
    wiki_train_ids: list[int]
    router_spec: RouterSpec
    seen_items: list[dict[str, list[TrainItem]]]  # per replicate: the first 300 of its training draw in the stored 220907 order, per capability
    teacher_outputs: dict[str, dict[str, list[str]]] = field(default_factory=dict)  # capability (teacher) -> panel name -> stored output text per item (data-generation step)
    device: torch.device = field(default_factory=lambda: torch.device("cpu"))
    seed_mode_name: str = "test"

    def plan(self, r: int) -> core.SeedPlan:
        return core.SeedPlan(self.mode, r)

    def codes(self, r: int) -> CodeBook:
        return CodeBook(self.plan(r).code_seed(), self.vocabulary)

    def train_examples(self, r: int, task: str) -> list[Example]:
        return [self.bank.train(task, x) for x in self.streams[r].t[task]]

    def gold_examples(self, r: int, task: str) -> list[Example]:
        return [self.bank.train(task, x) for x in self.streams[r].gold[task]]

    @property
    def marker_index(self) -> int:
        return self.vocabulary


# --- snapshot files (immutable, with a manifest and hash) ------------------------------------------------------------------------------------------
def _arm_state(arm: Arm) -> dict[str, Any]:
    if isinstance(arm, MemoryArm):
        return {"kind": "memory", "layer": arm.layer, "store": arm.store.snapshot_state()}
    if isinstance(arm, LoRAArm):
        return {"kind": "lora", "rank": arm.adapter.rank, "state": {k: v.detach().clone() for k, v in arm.adapter.state_dict().items()}}
    if isinstance(arm, TableArm):
        return {"kind": "table", "task": arm.task, "layer": arm.layer, "vocabulary": arm.vocabulary, "table": arm.table.detach().clone(), "gate": arm.gate.detach().clone()}
    raise ValueError(f"cannot snapshot arm kind {arm.kind!r}")


def save_arm(arm: Arm, directory: Path, name: str) -> dict[str, Any]:
    """Write ``name.pt`` and ``name.manifest.json`` (file hash and arm hash). Immutable: an existing snapshot is refused."""
    directory.mkdir(parents=True, exist_ok=True)
    safe = name.replace("/", "__").replace("@", "_at_")
    data, manifest = directory / f"{safe}.pt", directory / f"{safe}.manifest.json"
    if data.exists() or manifest.exists():
        raise FileExistsError(f"snapshot {name!r} exists and is immutable")
    tmp = directory / f".{safe}.tmp"
    torch.save(_arm_state(arm), tmp)
    atomic_write(data, tmp.read_bytes())
    tmp.unlink()
    m = {"name": name, "kind": arm.kind, "file": data.name, "file_sha256": file_sha256(data), "arm_hash": arm.state_hash()}
    atomic_write(manifest, (json.dumps(m, sort_keys=True) + "\n").encode())
    return m


def load_arm(world: World, r: int, directory: Path, name: str) -> Arm:
    """Load a snapshot (weights-only), verifying the file hash and the arm hash; the arm is frozen (scoring never trains)."""
    safe = name.replace("/", "__").replace("@", "_at_")
    data, manifest = directory / f"{safe}.pt", directory / f"{safe}.manifest.json"
    m = json.loads(manifest.read_text())
    if file_sha256(data) != m["file_sha256"]:
        raise ValueError(f"snapshot {name!r} does not hash to its manifest")
    st = torch.load(data, weights_only=True)
    arm: Arm
    if st["kind"] == "memory":
        arm = MemoryArm(SparseStore.from_state(st["store"]), st["layer"], world.codes(r))
        arm.store.set_trainable([])
    elif st["kind"] == "lora":
        ad = LoRAAdapter(world.cfg, st["rank"], None)  # zeros, overwritten by the stored state: no generator is used
        ad.load_state_dict(st["state"])
        arm = LoRAArm(ad)
    elif st["kind"] == "table":
        t = TableArm(st["task"], st["table"].shape[1], st["vocabulary"], st["layer"], None)
        t.table.data.copy_(st["table"])
        t.gate.data.copy_(st["gate"])
        arm = t
    else:
        raise ValueError(st["kind"])
    if arm.state_hash() != m["arm_hash"]:
        raise ValueError(f"snapshot {name!r} arm hash differs after loading")
    return arm


def snapshot_versions(directory: Path) -> VersionStore:
    return VersionStore(directory / "versions")
