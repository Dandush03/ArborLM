# ruff: noqa: E501
"""P9 physical layouts for general N (package I4): identity, frequency packing, sparse co-access,
random partition, branch-constrained co-access and the oracle cluster layout.

Specification: ADR-0017 section 8.4 (comparison layouts, oracle layout, calibration-only fitting).
Layouts are fitted on a **calibration** trace only and applied to evaluation traces;
``require_calibration`` is the guard. The P7-B layout code fixes 4,096 slots (``layout_from_pages``,
``coax_pages``, ``group_coax_pages`` use ``SLOTS``), uses a dense co-access matrix in ``pair_affinity``
(16 GiB at 65,536 slots) and writes 16-bit layout files, so those pieces are re-implemented here with a
sparse pair count and 32-bit files. The size-independent P7-B functions ``greedy_pages``,
``refine_pages`` and ``group_order`` are imported and called unchanged, so the co-access layout is the
same algorithm as P7-B's L-COAX (greedy page filling by pair affinity, then at most
``MAX_PASSES`` = 12 swap-refinement passes) and equals it exactly at 4,096 slots
(``sim.p7b_equivalence``). Nothing in ``arborlm`` is modified or monkeypatched.

Conventions: a ``Layout`` stores ``order [N] int64`` with ``order[p]`` the slot at position ``p``; the
page of slot ``s`` at ``R`` rows per page is ``position_of[s] // R``.

Status: implementation self-check only. Not independent review, not Astra validation.
"""

import struct
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import torch
from torch import Tensor

from arborlm.io import atomic_write, read_json, sha256, write_json
from arborlm.p7b_core import MAX_PASSES
from arborlm.p7b_layout import Adjacency, greedy_pages, group_order, refine_pages

from .core import Trace

LAYOUT_NAMES = (
    "identity",
    "frequency",
    "coaccess",
    "random_partition",
    "branch_coaccess",
    "oracle_cluster",
)
TOP = 8  # slots selected per query (ADR 5.1)
_PAIR_CHUNK_QUERIES = 32768


class LayoutError(ValueError):
    """A layout is not a permutation, or does not keep a required group contiguous."""


@dataclass
class Layout:
    """A slot-to-position permutation. ``name`` in ``LAYOUT_NAMES`` (or a caller-given control name such
    as ``partition_coaccess_1``); ``rows`` is the rows-per-page the layout was fitted for (None when it
    does not depend on R); ``info`` records fit statistics (JSON-serializable)."""

    name: str
    rows: int | None
    order: Tensor
    info: dict[str, Any] = field(default_factory=dict)
    _positions: Tensor | None = field(default=None, init=False, repr=False, compare=False)

    def positions(self) -> Tensor:
        """``[N] int64`` inverse permutation: position of each slot."""
        if self._positions is None:
            order = self.order.to(torch.int64)
            inverse = torch.empty_like(order)
            inverse[order] = torch.arange(order.numel(), dtype=torch.int64)
            self._positions = inverse
        return self._positions

    def key(self) -> str:
        """``name`` or ``name@R``; the key used in ``SimRecord.layout``."""
        return self.name if self.rows is None else f"{self.name}@{self.rows}"


@dataclass
class SparseCoaccess:
    """Pair counts of slots selected together by one query (and the per-slot access counts), stored
    sparsely: ``pairs [M, 2] int64`` with ``pairs[:, 0] < pairs[:, 1]``, ``counts [M] int64``,
    ``frequency [N] int64``. Memory is O(M), never O(N^2)."""

    slots: int
    pairs: Tensor
    counts: Tensor
    frequency: Tensor


def require_calibration(trace: Trace) -> Trace:
    """Return ``trace`` if its stream is ``calibration`` and refuse an evaluation stream (layouts are
    fitted on the calibration stream only, ADR 8.4). Anything that is not a ``Trace`` raises
    ``TypeError``; a trace of another stream raises ``ValueError``."""
    if not isinstance(trace, Trace):
        raise TypeError(
            f"layout builders accept a calibration Trace only, not {type(trace).__name__}"
        )
    if trace.stream != "calibration":
        raise ValueError(
            f"layouts are fitted on the calibration stream only; got stream {trace.stream!r}"
        )
    return trace


def _check_selected(trace: Trace) -> Tensor:
    selected = trace.selected.to(torch.int64)
    if selected.dim() != 2 or int(selected.shape[1]) != TOP:
        raise ValueError(f"selected must have shape [Q, {TOP}], got {tuple(selected.shape)}")
    if selected.numel() and (int(selected.min()) < 0 or int(selected.max()) >= trace.slots):
        raise ValueError("selected slot id out of range")
    return selected


def sparse_coaccess(trace: Trace) -> SparseCoaccess:
    """Count co-selected slot pairs and per-slot frequencies in ``trace.selected [Q, 8]``.

    Each query contributes once per unordered pair of its distinct slots (the same count as P7-B's
    ``pair_affinity``, kept as a sparse list of unique pairs)."""
    selected = _check_selected(trace)
    n = int(trace.slots)
    frequency = torch.bincount(selected.flatten(), minlength=n)
    width = int(selected.shape[1])
    first = torch.tensor([a for a in range(width) for b in range(a + 1, width)], dtype=torch.int64)
    second = torch.tensor([b for a in range(width) for b in range(a + 1, width)], dtype=torch.int64)
    key_parts: list[Tensor] = []
    count_parts: list[Tensor] = []
    for start in range(0, int(selected.shape[0]), _PAIR_CHUNK_QUERIES):
        block = selected[start : start + _PAIR_CHUNK_QUERIES]
        left, right = block[:, first], block[:, second]
        low, high = torch.minimum(left, right), torch.maximum(left, right)
        keep = low != high  # a repeated slot inside one query forms no pair
        keys = (low * n + high)[keep]
        unique, counts = torch.unique(keys, return_counts=True)
        key_parts.append(unique)
        count_parts.append(counts)
    if not key_parts:
        empty = torch.zeros(0, dtype=torch.int64)
        return SparseCoaccess(n, torch.zeros(0, 2, dtype=torch.int64), empty, frequency)
    keys_all = torch.cat(key_parts)
    counts_all = torch.cat(count_parts)
    unique_all, inverse = torch.unique(keys_all, return_inverse=True)
    totals = torch.zeros(unique_all.numel(), dtype=torch.int64)
    totals.index_add_(0, inverse, counts_all)
    pairs = torch.stack([unique_all // n, unique_all % n], dim=1)
    return SparseCoaccess(n, pairs, totals, frequency)


def adjacency(co: SparseCoaccess) -> Adjacency:
    """The dict-of-dicts adjacency P7-B's ``greedy_pages`` / ``refine_pages`` consume (both directions)."""
    adj: Adjacency = {}
    for (a, b), c in zip(co.pairs.tolist(), co.counts.tolist(), strict=True):
        adj.setdefault(a, {})[b] = c
        adj.setdefault(b, {})[a] = c
    return adj


def _order_tensor(pages: Sequence[Sequence[int]], slots: int) -> Tensor:
    order = torch.tensor([s for page in pages for s in page], dtype=torch.int64)
    if order.numel() != slots:
        raise LayoutError(f"pages hold {order.numel()} slots, expected {slots}")
    return order


def identity_layout(slots: int) -> Layout:
    return Layout("identity", None, torch.arange(slots, dtype=torch.int64))


def frequency_layout(calibration: Trace) -> Layout:
    """Slots sorted by calibration access count descending, ties by slot id (P7-A's L-FREQ rule)."""
    cal = require_calibration(calibration)
    selected = _check_selected(cal)
    frequency = torch.bincount(selected.flatten(), minlength=cal.slots)
    order = torch.sort(-frequency, stable=True).indices  # ties keep ascending slot id
    return Layout("frequency", None, order.to(torch.int64))


def coaccess_layout(
    calibration: Trace,
    rows: int,
    *,
    seed: int,
    refine_rounds: int = MAX_PASSES,
    co: SparseCoaccess | None = None,
) -> Layout:
    """Optimized co-access layout for ``rows`` slots per page fitted on ``calibration``, unconstrained
    for flat and tree alike (ADR 8.4). It is P7-B's L-COAX algorithm on sparse pair counts: greedy page
    filling by pair affinity (P7-B ``greedy_pages``), then at most ``refine_rounds`` passes of bounded
    swap refinement (P7-B ``refine_pages``; P7-B's registered bound is ``MAX_PASSES`` = 12, the default
    here so that the result equals P7-B's at 4,096 slots). The algorithm has no random element:
    ``seed`` is recorded in ``info`` and consumes nothing, so the result is deterministic. Slots that
    were never accessed come after every accessed slot in the greedy fill (id order); refinement may
    exchange one of them into a hotter page, as in P7-B. ``co`` lets a caller reuse one sparse count
    across several R."""
    cal = require_calibration(calibration)
    if rows < 1:
        raise ValueError("rows must be at least 1")
    counts = co if co is not None else sparse_coaccess(cal)
    adj = adjacency(counts)
    f = counts.frequency.tolist()
    pages = greedy_pages(range(cal.slots), rows, f, adj)
    pages, refine_info = refine_pages(pages, adj, f, max_passes=refine_rounds)
    info = {
        "algorithm": "P7-B L-COAX (greedy_pages + refine_pages), sparse pair counts",
        "seed": seed,
        "seed_consumed": False,
        "refine_rounds_max": refine_rounds,
        "pair_entries": int(counts.counts.numel()),
        **refine_info,
    }
    return Layout("coaccess", rows, _order_tensor(pages, cal.slots), info)


def random_partition_layout(slots: int, rows: int, seed: int) -> Layout:
    """Seeded random permutation (a random partition into pages of ``rows`` slots)."""
    generator = torch.Generator().manual_seed(seed)
    order = torch.randperm(slots, generator=generator).to(torch.int64)
    return Layout("random_partition", rows, order, {"seed": seed})


def group_coaccess_layout(
    calibration: Trace,
    rows: int,
    groups: Sequence[Sequence[int]],
    *,
    name: str,
    seed: int = 0,
    refine_rounds: int = MAX_PASSES,
    co: SparseCoaccess | None = None,
) -> Layout:
    """Co-access layout with every group of slots contiguous: groups ordered by descending total
    calibration count (ties by group index), greedy page fill inside each group, then refinement with
    swap partners restricted to the same group. This is P7-B's ``group_coax_pages`` for ``rows`` no
    larger than a group (P7-B's special case for pages of two groups is not needed at R <= 32 and not
    implemented: ``ValueError``). ``branch_coaccess_layout`` and the P8 partition layouts (L-PCOAX, used
    only by the equivalence check) are instances."""
    cal = require_calibration(calibration)
    if any(len(g) < rows for g in groups):
        raise ValueError("a page larger than a group is not supported")
    counts = co if co is not None else sparse_coaccess(cal)
    adj = adjacency(counts)
    f = counts.frequency.tolist()
    group_of = [-1] * cal.slots
    for g, members in enumerate(groups):
        for slot in members:
            group_of[slot] = g
    if min(group_of) < 0:
        raise ValueError("groups must cover every slot")
    pages: list[list[int]] = []
    for g in group_order(groups, f):
        pages += greedy_pages(groups[g], rows, f, adj)
    pages, refine_info = refine_pages(pages, adj, f, group_of=group_of, max_passes=refine_rounds)
    info = {
        "algorithm": "P7-B group_coax_pages (greedy_pages + refine_pages), sparse pair counts",
        "seed": seed,
        "seed_consumed": False,
        "groups": len(groups),
        "refine_rounds_max": refine_rounds,
        **refine_info,
    }
    layout = Layout(name, rows, _order_tensor(pages, cal.slots), info)
    verify_layout(layout, cal.slots, [list(g) for g in groups])
    return layout


def branch_coaccess_layout(
    calibration: Trace, rows: int, *, branches: int, per_branch: int, seed: int
) -> Layout:
    """Tree control: each branch's ``per_branch`` slots contiguous (branch ``b`` owns slots
    ``b * per_branch .. (b + 1) * per_branch - 1``, as in P5's constant-candidate tree); branches in
    descending total calibration count, co-access order inside each branch. Reported as a control only."""
    cal = require_calibration(calibration)
    if branches * per_branch != cal.slots:
        raise ValueError("branches * per_branch must equal the number of slots")
    groups = [list(range(b * per_branch, (b + 1) * per_branch)) for b in range(branches)]
    return group_coaccess_layout(cal, rows, groups, name="branch_coaccess", seed=seed)


def oracle_cluster_layout(calibration: Trace, clusters: int) -> Layout:
    """Bound (ADR 8.4): each slot goes to the cluster with most of its calibration accesses (ties to
    the lowest cluster number), clusters contiguous in cluster order, within a cluster by slot id;
    never-accessed slots last in id order. Uses ``calibration.cluster`` (queries with -1 are ignored)."""
    cal = require_calibration(calibration)
    selected = _check_selected(cal)
    n = int(cal.slots)
    cluster = cal.cluster.to(torch.int64)
    if cluster.shape[0] != selected.shape[0]:
        raise ValueError("cluster must have one entry per query")
    valid = cluster >= 0
    if bool(valid.any()) and int(cluster[valid].max()) >= clusters:
        raise ValueError("a cluster id is not below the given number of clusters")
    chosen = torch.full((n,), clusters, dtype=torch.int64)  # `clusters` = never accessed -> last
    if bool(valid.any()):
        rows_sel = selected[valid]
        cl = cluster[valid].unsqueeze(1).expand(-1, rows_sel.shape[1])
        keys = (rows_sel * clusters + cl).flatten()
        unique, hits = torch.unique(keys, return_counts=True)
        slot, cid = unique // clusters, unique % clusters
        # per slot: the cluster with the most accesses, ties to the lowest cluster id. `unique` is
        # sorted by (slot, cluster), so a stable sort on -hits keeps the lowest cluster first.
        by_hits = torch.sort(-hits, stable=True).indices
        by_slot = by_hits[torch.sort(slot[by_hits], stable=True).indices]
        slot_sorted = slot[by_slot]
        is_first = torch.ones_like(slot_sorted, dtype=torch.bool)
        is_first[1:] = slot_sorted[1:] != slot_sorted[:-1]
        chosen[slot_sorted[is_first]] = cid[by_slot][is_first]
    slot_ids = torch.arange(n, dtype=torch.int64)
    order = slot_ids[torch.sort(chosen, stable=True).indices]  # by cluster, then slot id
    info = {
        "clusters": clusters,
        "assigned_slots": int((chosen < clusters).sum()),
        "unassigned_slots": int((chosen >= clusters).sum()),
    }
    return Layout("oracle_cluster", None, order, info)


def build_layouts(
    calibration: Trace,
    rows_list: tuple[int, ...],
    *,
    arch: str,
    seed: int,
    clusters: int,
    branches: int = 0,
    per_branch: int = 0,
    refine_rounds: int = MAX_PASSES,
) -> dict[str, Layout]:
    """All layouts a cell needs, keyed by ``Layout.key()``: identity, frequency and the oracle cluster
    layout (independent of R), co-access and random partition per R in ``rows_list``, and (trees) the
    branch-constrained co-access layout per R. ``seed`` is the random-partition seed. Every layout is
    verified with ``verify_layout``."""
    cal = require_calibration(calibration)
    tree = arch in ("fixed_tree", "learned_tree")
    if tree and (branches < 1 or per_branch < 1):
        raise ValueError("a tree cell needs branches and per_branch")
    out: dict[str, Layout] = {}
    for layout in (
        identity_layout(cal.slots),
        frequency_layout(cal),
        oracle_cluster_layout(cal, clusters),
    ):
        out[layout.key()] = layout
    co = sparse_coaccess(cal)
    for rows in rows_list:
        built = [
            coaccess_layout(cal, rows, seed=seed, refine_rounds=refine_rounds, co=co),
            random_partition_layout(cal.slots, rows, seed),
        ]
        if tree:
            groups = [list(range(b * per_branch, (b + 1) * per_branch)) for b in range(branches)]
            built.append(
                group_coaccess_layout(
                    cal,
                    rows,
                    groups,
                    name="branch_coaccess",
                    seed=seed,
                    refine_rounds=refine_rounds,
                    co=co,
                )
            )
        for layout in built:
            out[layout.key()] = layout
    for layout in out.values():
        verify_layout(layout, cal.slots)
    return out


def verify_layout(layout: Layout, slots: int, groups: list[list[int]] | None = None) -> None:
    """Raise ``LayoutError`` unless ``layout.order`` is a permutation of ``range(slots)`` (and each of
    ``groups`` is contiguous when given)."""
    order = layout.order
    if order.dim() != 1 or int(order.numel()) != slots:
        raise LayoutError(
            f"layout {layout.key()} has {tuple(order.shape)} entries, expected {slots}"
        )
    seen = torch.zeros(slots, dtype=torch.bool)
    if int(order.min()) < 0 or int(order.max()) >= slots:
        raise LayoutError(f"layout {layout.key()} holds a slot id outside 0..{slots - 1}")
    seen[order.to(torch.int64)] = True
    if not bool(seen.all()):
        raise LayoutError(f"layout {layout.key()} is not a permutation of 0..{slots - 1}")
    if groups is not None:
        positions = layout.positions()
        for g, members in enumerate(groups):
            places = positions[torch.tensor(members, dtype=torch.int64)]
            if int(places.max()) - int(places.min()) + 1 != len(members):
                raise LayoutError(f"layout {layout.key()} does not keep group {g} contiguous")


# --- 32-bit layout files ----------------------------------------------------------------------------------
def _pack_order(order: Tensor) -> bytes:
    values = order.to(torch.int64).tolist()
    return struct.pack(f"<{len(values)}i", *values)


def _unpack_order(data: bytes) -> Tensor:
    count = len(data) // 4
    if count * 4 != len(data):
        raise LayoutError("layout data length is not a whole number of int32 entries")
    if sys.byteorder == "little":
        return torch.frombuffer(bytearray(data), dtype=torch.int32).to(torch.int64)
    return torch.tensor(struct.unpack(f"<{count}i", data), dtype=torch.int64)  # pragma: no cover


def index_path(path: Path) -> Path:
    return path.with_name(path.name + ".index.json")


def write_layouts(path: Path, layouts: dict[str, Layout]) -> dict[str, str]:
    """Write one binary file of little-endian int32 orders (concatenated, in the dict's order) and a
    sibling ``<name>.index.json``; returns key -> SHA-256 of that layout's int32 order bytes."""
    blob = bytearray()
    entries: list[dict[str, Any]] = []
    hashes: dict[str, str] = {}
    for key, layout in layouts.items():
        if layout.key() != key:
            raise ValueError(f"layout stored under {key!r} has key {layout.key()!r}")
        data = _pack_order(layout.order)
        digest = sha256(data)
        entries.append(
            {
                "key": key,
                "name": layout.name,
                "rows": layout.rows,
                "slots": int(layout.order.numel()),
                "offset_bytes": len(blob),
                "sha256": digest,
                "info": layout.info,
            }
        )
        hashes[key] = digest
        blob += data
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(path, bytes(blob))
    write_json(
        index_path(path),
        {"dtype": "<i4", "file": path.name, "file_sha256": sha256(bytes(blob)), "layouts": entries},
    )
    return hashes


def read_layouts(path: Path, expected: dict[str, str] | None = None) -> dict[str, Layout]:
    """Read a file written by ``write_layouts``; verifies the file hash, every layout hash (against the
    index and, when given, against ``expected``) and that every layout is a permutation."""
    index = read_json(index_path(path))
    data = path.read_bytes()
    if sha256(data) != index["file_sha256"]:
        raise LayoutError(f"layout file hash differs from its index: {path}")
    out: dict[str, Layout] = {}
    for entry in index["layouts"]:
        start = int(entry["offset_bytes"])
        chunk = data[start : start + 4 * int(entry["slots"])]
        digest = sha256(chunk)
        if digest != entry["sha256"]:
            raise LayoutError(f"layout {entry['key']} hash differs from its index")
        if expected is not None and expected.get(entry["key"]) != digest:
            raise LayoutError(f"layout {entry['key']} hash differs from the expected one")
        layout = Layout(entry["name"], entry["rows"], _unpack_order(chunk), entry["info"])
        verify_layout(layout, int(entry["slots"]))
        out[entry["key"]] = layout
    if expected is not None and set(expected) - set(out):
        raise LayoutError(
            f"expected layouts missing from the file: {sorted(set(expected) - set(out))}"
        )
    return out
