# ruff: noqa: E501
"""The expandable sparse store, its stages and versions, the oracle codes, and the arms that apply a store, an E-table or a LoRA adapter to the student (ADR-0022 sections 3, 5.4, 6.3, 7).

Store (section 3). Rows s = 1..S with keys k_s in R^16, values V_s in R^d and a stage index. For a unit query q: a_s = q . k_s / |k_s|; the 8 largest are selected, ties broken by the
lowest row index (a stable sort); weights softmax(a / 0.2) over the selected; r = sum_s w_s g_{stage(s)} V_s, added to the output of block L at the read position. Keys and values are
drawn from N(0, 0.02) by one generator, keys first; the gate is a scalar with initial value 0, one per stage. Freezing a stage freezes its keys, values and gate.

Every memory and every adapter arm is applied only under its route: an arm given no reads (route "none") applies nothing.
"""

import copy
import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import torch
from torch import Tensor, nn

from arborlm.io import atomic_write, file_sha256, sha256
from studies.p9.model import unit_code

from . import core
from .model import LoRAAdapter, Student, StudentConfig, tensor_sha

Read = tuple[int, str, int]  # (position, task, vocabulary index j; core.MARKER_INDEX for the task marker)


# --- oracle codes (section 5.4) --------------------------------------------------------------------------------------------------------------
def code_identifier(task: str, j: int) -> int:
    """2,001 * tau + j, tau = 0 for A and 1 for B, j the word's index (j = 2,000 for the task marker); the vocabulary size enters as 2,001 = vocabulary + 1."""
    return (core.VOCABULARY + 1) * core.TASK_NUMBER[task] + j


class CodeBook:
    """Fixed random unit vectors from a seeded hash of the (seed, identifier) pair (P9's ``unit_code``): no generator is seeded. ``seed`` is the replicate's +10 seed. ``vocabulary`` may
    be smaller than 2,000 in the dry stage; the identifier layout then follows ``vocabulary + 1``."""

    def __init__(self, seed: int, vocabulary: int | None = None) -> None:
        self.seed = seed
        self.vocabulary = vocabulary if vocabulary is not None else core.VOCABULARY
        self._cache: dict[tuple[str, int], Tensor] = {}

    def ident(self, task: str, j: int) -> int:
        return (self.vocabulary + 1) * core.TASK_NUMBER[task] + j

    def get(self, task: str, j: int) -> Tensor:
        key = (task, j)
        if key not in self._cache:
            self._cache[key] = torch.tensor(unit_code(self.seed, self.ident(task, j), core.KEY_WIDTH), dtype=torch.float32)
        return self._cache[key]

    @property
    def marker(self) -> int:
        return self.vocabulary


# --- the store --------------------------------------------------------------------------------------------------------------------------------
def fresh_stage(generator: torch.Generator, rows: int, width: int) -> tuple[Tensor, Tensor]:
    """Keys (rows, 16) then values (rows, width), both N(0, 0.02), from one generator in that order."""
    keys = core.INIT_STD * torch.randn(rows, core.KEY_WIDTH, generator=generator)
    values = core.INIT_STD * torch.randn(rows, width, generator=generator)
    return keys, values


class SparseStore(nn.Module):
    def __init__(self, width: int) -> None:
        super().__init__()
        self.width = width
        self.keys = nn.ParameterList()
        self.values = nn.ParameterList()
        self.gates = nn.ParameterList()
        self.stage_rows: list[int] = []

    # -- construction -------------------------------------------------------------------------------------------------------------------------
    @staticmethod
    def new(width: int, rows: int, generator: torch.Generator) -> "SparseStore":
        s = SparseStore(width)
        s.append_stage(rows, generator)
        return s

    def append_stage(self, rows: int, generator: torch.Generator) -> int:
        """Append ``rows`` rows with their own gate (initial value 0), keys then values from ``generator``. Returns the new stage index. Earlier rows are untouched."""
        keys, values = fresh_stage(generator, rows, self.width)
        self.keys.append(nn.Parameter(keys))
        self.values.append(nn.Parameter(values))
        self.gates.append(nn.Parameter(torch.zeros(1)))
        self.stage_rows.append(rows)
        return len(self.stage_rows) - 1

    @property
    def rows(self) -> int:
        return sum(self.stage_rows)

    @property
    def stages(self) -> int:
        return len(self.stage_rows)

    def stage_parameters(self, stage: int) -> list[nn.Parameter]:
        return [self.keys[stage], self.values[stage], self.gates[stage]]

    def freeze_stage(self, stage: int) -> None:
        for p in self.stage_parameters(stage):
            p.requires_grad_(False)

    def set_trainable(self, stages: Sequence[int]) -> None:
        for k in range(self.stages):
            for p in self.stage_parameters(k):
                p.requires_grad_(k in stages)

    def trainable(self) -> list[nn.Parameter]:
        return [p for p in self.parameters() if p.requires_grad]

    # -- the read ------------------------------------------------------------------------------------------------------------------------------
    def read(self, q: Tensor) -> Tensor:
        """The read of unit queries ``q`` (M, 16): (M, width). Top-8 by cosine with the lowest row index winning ties; softmax at temperature 0.2; per-stage gates."""
        keys = torch.cat(list(self.keys), dim=0)
        values = torch.cat(list(self.values), dim=0)
        gate = torch.cat([g.expand(r) for g, r in zip(self.gates, self.stage_rows, strict=True)])
        kn = keys / keys.norm(dim=-1, keepdim=True).clamp_min(1e-12)
        a = q @ kn.t()
        order = torch.sort(a, dim=-1, descending=True, stable=True).indices[:, : core.TOP]
        sel = torch.gather(a, 1, order)
        w = torch.softmax(sel / core.TEMPERATURE, dim=-1)
        return ((w * gate[order]).unsqueeze(-1) * values[order]).sum(dim=1)

    def selected_rows(self, q: Tensor) -> Tensor:
        keys = torch.cat(list(self.keys), dim=0)
        kn = keys / keys.norm(dim=-1, keepdim=True).clamp_min(1e-12)
        return torch.sort(q @ kn.t(), dim=-1, descending=True, stable=True).indices[:, : core.TOP]

    def read_weights(self, q: Tensor) -> tuple[Tensor, Tensor]:
        """(selected row indices, softmax weights) of a read, for the append-cost and interference reports."""
        keys = torch.cat(list(self.keys), dim=0)
        kn = keys / keys.norm(dim=-1, keepdim=True).clamp_min(1e-12)
        a = q @ kn.t()
        order = torch.sort(a, dim=-1, descending=True, stable=True).indices[:, : core.TOP]
        return order, torch.softmax(torch.gather(a, 1, order) / core.TEMPERATURE, dim=-1)

    # -- state ---------------------------------------------------------------------------------------------------------------------------------
    def snapshot_state(self) -> dict[str, Any]:
        return {"width": self.width, "stage_rows": list(self.stage_rows), "keys": [p.detach().clone() for p in self.keys], "values": [p.detach().clone() for p in self.values], "gates": [p.detach().clone() for p in self.gates]}

    @staticmethod
    def from_state(state: dict[str, Any]) -> "SparseStore":
        s = SparseStore(int(state["width"]))
        for k, v, g, r in zip(state["keys"], state["values"], state["gates"], state["stage_rows"], strict=True):
            s.keys.append(nn.Parameter(k.clone()))
            s.values.append(nn.Parameter(v.clone()))
            s.gates.append(nn.Parameter(g.clone()))
            s.stage_rows.append(int(r))
        return s

    def content_hash(self) -> str:
        parts = [json.dumps(self.stage_rows)]
        for k in range(self.stages):
            parts += [tensor_sha(self.keys[k]), tensor_sha(self.values[k]), tensor_sha(self.gates[k])]
        return sha256("|".join(parts).encode())

    def clone(self) -> "SparseStore":
        c = SparseStore.from_state(self.snapshot_state())
        for k in range(self.stages):
            for p, q in zip(self.stage_parameters(k), c.stage_parameters(k), strict=True):
                q.requires_grad_(p.requires_grad)
        return c

    def parameter_count(self) -> int:
        return sum(p.numel() for p in self.parameters())


# --- version store (section 3: immutable snapshots with manifest and content hash) -----------------------------------------------------------------
class VersionRefused(RuntimeError):
    pass


class VersionStore:
    """Every store state is an immutable snapshot with a manifest and a content hash. A reader pinned to an earlier version is unaffected while a later one is prepared; rollback is the
    pinning of the earlier manifest. Engineering property, tested; not a result."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self._pinned: str | None = None

    def _paths(self, name: str) -> tuple[Path, Path]:
        return self.root / f"{name}.pt", self.root / f"{name}.manifest.json"

    def publish(self, name: str, store: SparseStore, parent: str | None = None) -> dict[str, Any]:
        data, manifest = self._paths(name)
        if data.exists() or manifest.exists():
            raise VersionRefused(f"version {name!r} exists and is immutable")
        if parent is not None and not self._paths(parent)[1].exists():
            raise VersionRefused(f"parent version {parent!r} does not exist")
        tmp = self.root / f".{name}.tmp.pt"
        torch.save(store.snapshot_state(), tmp)
        atomic_write(data, tmp.read_bytes())
        tmp.unlink()
        m = {"name": name, "parent": parent, "file": data.name, "file_sha256": file_sha256(data), "content_hash": store.content_hash(), "stage_rows": list(store.stage_rows)}
        atomic_write(manifest, (json.dumps(m, sort_keys=True) + "\n").encode())
        return m

    def manifest(self, name: str) -> dict[str, Any]:
        loaded: dict[str, Any] = json.loads(self._paths(name)[1].read_text())
        return loaded

    def load(self, name: str) -> SparseStore:
        data, _ = self._paths(name)
        m = self.manifest(name)
        if file_sha256(data) != m["file_sha256"]:
            raise VersionRefused(f"version {name!r} does not hash to its manifest")
        store = SparseStore.from_state(torch.load(data, weights_only=True))
        if store.content_hash() != m["content_hash"]:
            raise VersionRefused(f"version {name!r} content hash differs after loading")
        return store

    def pin(self, name: str) -> None:
        self.manifest(name)
        self._pinned = name

    def pinned(self) -> SparseStore:
        if self._pinned is None:
            raise VersionRefused("no version is pinned")
        return self.load(self._pinned)


# --- ablations and permutation controls (section 7) ------------------------------------------------------------------------------------------------
ABLATION_KINDS = ("off", "value_perm", "code_perm", "marker_only", "words_only")


@dataclass
class Ablation:
    kind: str
    value_perms: dict[int, Tensor] = field(default_factory=dict)  # stage -> permutation of that stage's value rows (among themselves)
    code_perm: Tensor | None = None  # permutation of word indices (marker kept)
    code_tasks: tuple[str, ...] = ()  # tasks whose word codes are permuted

    def __post_init__(self) -> None:
        if self.kind not in ABLATION_KINDS:
            raise ValueError(f"unknown ablation {self.kind!r}")


def make_ablation(kind: str, store: SparseStore | None, generator: torch.Generator, *, stages: Sequence[int], tasks: Sequence[str], vocabulary: int) -> Ablation:
    """The ablation of one kind. The permutation controls draw from ``generator`` (a fresh +4 generator, one per use): value permutations stage by stage (in the order given), then
    the word-code permutation over ``vocabulary`` words. ``stages`` are the store stages whose values are permuted among themselves and ``tasks`` the tasks whose word codes are permuted:
    for a stage-2 store, the second stage and the second task only (section 7); for a single-stage store, all."""
    if kind == "value_perm":
        assert store is not None
        return Ablation(kind, {k: torch.randperm(store.stage_rows[k], generator=generator) for k in stages})
    if kind == "code_perm":
        return Ablation(kind, code_perm=torch.randperm(vocabulary, generator=generator), code_tasks=tuple(tasks))
    return Ablation(kind)


def permuted_values_store(store: SparseStore, perms: dict[int, Tensor]) -> SparseStore:
    c = store.clone()
    with torch.no_grad():
        for k, perm in perms.items():
            c.values[k].copy_(store.values[k][perm])
    return c


def apply_read_ablation(reads: Sequence[Read], ab: Ablation | None, marker_index: int) -> list[Read]:
    if ab is None:
        return list(reads)
    if ab.kind == "off":
        return []
    if ab.kind == "marker_only":
        return [r for r in reads if r[2] == marker_index]
    if ab.kind == "words_only":
        return [r for r in reads if r[2] != marker_index]
    if ab.kind == "code_perm" and ab.code_perm is not None:
        return [(p, t, int(ab.code_perm[j]) if (j != marker_index and t in ab.code_tasks) else j) for p, t, j in reads]
    return list(reads)


# --- arms: what the student receives (section 6.3, 7) -----------------------------------------------------------------------------------------------
class Arm:
    """Interface of everything applied to the student. ``prepare`` returns ``(add, adapter)`` for a batch of read lists (one list per example; an empty list is route "none")."""

    kind = "none"
    layer: int | None = None

    def trainable(self) -> list[nn.Parameter]:
        return []

    def prepare(self, reads: Sequence[Sequence[Read]], batch: int, length: int, device: torch.device, ablation: Ablation | None = None) -> tuple[Tensor | None, LoRAAdapter | None]:
        return None, None

    def parameter_count(self) -> int:
        return 0

    def state_hash(self) -> str:
        return sha256(b"null")

    def to(self, device: torch.device) -> None:
        """Move the arm's tensors to ``device`` (training on MPS; scoring is always on CPU)."""


class NullArm(Arm):
    """Stage 0: the untrained student."""


class MemoryArm(Arm):
    kind = "memory"

    def __init__(self, store: SparseStore, layer: int, codes: CodeBook) -> None:
        self.store, self.layer, self.codes = store, layer, codes

    def trainable(self) -> list[nn.Parameter]:
        return self.store.trainable()

    def to(self, device: torch.device) -> None:
        self.store.to(device)

    def parameter_count(self) -> int:
        return self.store.parameter_count()

    def state_hash(self) -> str:
        return self.store.content_hash()

    def queries(self, reads: Sequence[Sequence[Read]]) -> tuple[Tensor, Tensor, Tensor]:
        bi: list[int] = []
        pi: list[int] = []
        q: list[Tensor] = []
        for b, rs in enumerate(reads):
            for pos, task, j in rs:
                bi.append(b)
                pi.append(pos)
                q.append(self.codes.get(task, j))
        if not q:
            return torch.zeros(0, dtype=torch.long), torch.zeros(0, dtype=torch.long), torch.zeros(0, core.KEY_WIDTH)
        return torch.tensor(bi), torch.tensor(pi), torch.stack(q)

    def prepare(self, reads: Sequence[Sequence[Read]], batch: int, length: int, device: torch.device, ablation: Ablation | None = None) -> tuple[Tensor | None, LoRAAdapter | None]:
        marker = self.codes.marker
        use = [apply_read_ablation(rs, ablation, marker) for rs in reads]
        if not any(use):
            return None, None
        store = permuted_values_store(self.store, ablation.value_perms) if ablation is not None and ablation.kind == "value_perm" else self.store
        bi, pi, q = self.queries(use)
        r = store.read(q.to(device))
        add = torch.zeros(batch, length, self.store.width, device=device, dtype=r.dtype)
        add = add.index_put((bi.to(device), pi.to(device)), r, accumulate=True)
        return add, None


class TableArm(Arm):
    """E-table (section 7): one trainable vector per vocabulary word and per task marker of one capability, added at layer L at the same positions as the store's reads, times one linear
    scalar gate with initial value 0. No keys and no top-k. Vectors from N(0, 0.02) with the +9 seed."""

    kind = "table"

    def __init__(self, task: str, width: int, vocabulary: int, layer: int, generator: torch.Generator | None) -> None:
        self.task, self.layer, self.vocabulary = task, layer, vocabulary
        self.table = nn.Parameter(torch.zeros(vocabulary + 1, width) if generator is None else core.INIT_STD * torch.randn(vocabulary + 1, width, generator=generator))
        self.gate = nn.Parameter(torch.zeros(1))

    def trainable(self) -> list[nn.Parameter]:
        return [self.table, self.gate]

    def to(self, device: torch.device) -> None:
        self.table.data = self.table.data.to(device)
        self.gate.data = self.gate.data.to(device)

    def parameter_count(self) -> int:
        return self.table.numel() + 1

    def state_hash(self) -> str:
        return sha256((tensor_sha(self.table) + tensor_sha(self.gate)).encode())

    def prepare(self, reads: Sequence[Sequence[Read]], batch: int, length: int, device: torch.device, ablation: Ablation | None = None) -> tuple[Tensor | None, LoRAAdapter | None]:
        if ablation is not None and ablation.kind == "off":
            return None, None
        bi: list[int] = []
        pi: list[int] = []
        js: list[int] = []
        for b, rs in enumerate(reads):
            for pos, task, j in rs:
                if task == self.task:
                    bi.append(b)
                    pi.append(pos)
                    js.append(j)
        if not js:
            return None, None
        dev = self.table.device
        vec = self.gate * self.table[torch.tensor(js, device=dev)]
        add = torch.zeros(batch, length, self.table.shape[1], device=device, dtype=vec.dtype)
        return add.index_put((torch.tensor(bi, device=dev), torch.tensor(pi, device=dev)), vec, accumulate=True), None


class LoRAArm(Arm):
    kind = "lora"

    def __init__(self, adapter: LoRAAdapter) -> None:
        self.adapter = adapter

    def trainable(self) -> list[nn.Parameter]:
        return [p for p in self.adapter.parameters() if p.requires_grad]

    def to(self, device: torch.device) -> None:
        self.adapter.to(device)

    def parameter_count(self) -> int:
        return sum(p.numel() for p in self.adapter.parameters())

    def state_hash(self) -> str:
        return sha256("|".join(tensor_sha(p) for p in self.adapter.parameters()).encode())

    def prepare(self, reads: Sequence[Sequence[Read]], batch: int, length: int, device: torch.device, ablation: Ablation | None = None) -> tuple[Tensor | None, LoRAAdapter | None]:
        if ablation is not None and ablation.kind == "off":
            return None, None
        if not any(reads):  # route "none": no adapter
            return None, None
        return None, self.adapter


def new_lora_arm(cfg: StudentConfig, rank: int, generator: torch.Generator) -> LoRAArm:
    return LoRAArm(LoRAAdapter(cfg, rank, generator))


def run_student(student: Student, arm: Arm, ids: Tensor, reads: Sequence[Sequence[Read]], ablation: Ablation | None = None) -> Tensor:
    """One forward pass of the student under an arm and a route (given by the reads)."""
    add, adapter = arm.prepare(reads, ids.shape[0], ids.shape[1], ids.device, ablation)
    student.read_layer = arm.layer
    logits: Tensor = student(ids, add=add, adapter=adapter)
    return logits


def clone_arm(arm: Arm) -> Arm:
    return copy.deepcopy(arm)


def row_shares(store: SparseStore, q: Tensor, first_stage_rows: int) -> dict[str, float]:
    """For a set of queries: the share of the top-8 weight that falls on rows beyond the first ``first_stage_rows`` (appended rows), and the share of reads that touch one. Used for the append-cost
    report; descriptive."""
    order, w = store.read_weights(q)
    new = order >= first_stage_rows
    return {"weight_on_new_rows": float((w * new).sum(dim=1).mean()), "reads_touching_new_rows": float(new.any(dim=1).float().mean())}

