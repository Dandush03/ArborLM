"""P7-B layout construction (ADR-0014 section 4): affinity, greedy page fill, bounded swap
refinement, branch- and partition-constrained variants, the R = 512 group rule, canonical hashes.

Everything here depends on a **calibration trace only**. The interface enforces that: every builder
takes a ``CalibrationTrace``, an object that can only be made from calibration files (or, for tests
and the dry run, from tensors the caller declares to be calibration). Passing any other object, in
particular an ``EvaluationTrace`` from the simulator module, raises ``TypeError``.

Affinity is kept sparse (dict of dicts keyed by slot ID, nonzero entries only).

Status: implementation self-checked only. Not independent review, not Astra validation.
"""

import random
import struct
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import torch
from torch import Tensor

from . import p7b_core as core
from .io import file_sha256, sha256

Adjacency = dict[int, dict[int, int]]


# --- the calibration-only interface
class CalibrationTrace:
    """A calibration trace: selected IDs ``[queries, 8]`` (and visited branches for trees).

    Construct with ``from_identity`` (real files, hash-verified, calibration role only) or
    ``declared`` (tensors the caller states are calibration; tests and the dry run).
    """

    __slots__ = ("branches", "kind", "label", "selected", "source")

    def __init__(
        self,
        selected: Tensor,
        branches: Tensor | None,
        kind: str,
        label: str,
        *,
        source: str,
        _token: object,
    ) -> None:
        if _token is not _CONSTRUCT:
            raise TypeError("use CalibrationTrace.from_identity or CalibrationTrace.declared")
        self.selected = selected.to(torch.int64)
        self.branches = None if branches is None else branches.to(torch.int64)
        self.kind, self.label, self.source = kind, label, source

    @classmethod
    def from_identity(cls, identity: core.Identity, label: str) -> "CalibrationTrace":
        """Read the two calibration files of ``label`` (never an evaluation file), verifying their
        recorded SHA-256 against the identity manifest."""
        from . import p7a_core as a_core

        _, kind = core.parse_label(label)
        directory, record = identity.trace_record(label, "calibration")
        for entry in record.values():
            if entry is not None and not entry["file"].startswith("calib_"):
                raise TypeError(
                    "layout construction refuses any file that is not a calibration file"
                )
        selected, branches = a_core.read_trace(directory, "calib", record)
        a_core.check_trace(selected, branches, kind, queries=int(selected.shape[0]))
        return cls(selected, branches, kind, label, source="identity-manifest", _token=_CONSTRUCT)

    @classmethod
    def declared(
        cls, selected: Tensor, branches: Tensor | None, kind: str, label: str
    ) -> "CalibrationTrace":
        return cls(selected, branches, kind, label, source="declared", _token=_CONSTRUCT)

    def counts(self) -> list[int]:
        return torch.bincount(self.selected.flatten(), minlength=core.SLOTS).tolist()


_CONSTRUCT = object()


def require_calibration(trace: object) -> CalibrationTrace:
    if not isinstance(trace, CalibrationTrace):
        raise TypeError(
            "layout builders accept a CalibrationTrace only; "
            f"{type(trace).__name__} is not a calibration trace"
        )
    return trace


# --- affinity
def _adjacency_from_matrix(matrix: Tensor, uniq: Tensor, n: int) -> Adjacency:
    nz = matrix.nonzero().flatten()
    if nz.numel() == 0:
        return {}
    values = matrix[nz].tolist()
    ids = uniq.tolist()
    adj: Adjacency = {}
    for flat, value in zip(nz.tolist(), values, strict=True):
        i, j = divmod(flat, n)
        adj.setdefault(ids[i], {})[ids[j]] = value
    return adj


def pair_affinity(selected: Tensor) -> Adjacency:
    """Same-query affinity (registered, W = 0): ``A[i][j]`` for i != j is the number of queries in
    which slots i and j are both selected. Symmetric; each query contributes once per unordered
    pair (and so once to each of the two ordered entries)."""
    selected = selected.to(torch.int64)
    uniq, inverse = torch.unique(selected, return_inverse=True)
    n = int(uniq.numel())
    matrix = torch.zeros(n * n, dtype=torch.int32)
    width = selected.shape[1]
    off = torch.tensor(
        [a * width + b for a in range(width) for b in range(width) if a != b], dtype=torch.int64
    )
    chunk = 4096
    for start in range(0, selected.shape[0], chunk):
        block = inverse[start : start + chunk]
        keys = (block.unsqueeze(2) * n + block.unsqueeze(1)).reshape(block.shape[0], -1)[:, off]
        matrix.index_add_(0, keys.flatten(), torch.ones(keys.numel(), dtype=torch.int32))
    return _adjacency_from_matrix(matrix, uniq, n)


def window_affinity(selected: Tensor, window: int = core.WINDOW) -> Adjacency:
    """Windowed affinity A8: N[i][j] counts ordered query pairs (t, u) in one 64-query context with
    0 <= t - u <= ``window`` (including t = u) such that i is selected at t and j at u, i != j;
    A8 = N + N^T."""
    selected = selected.to(torch.int64)
    queries, width = selected.shape
    contexts = queries // core.CONTEXT
    if contexts * core.CONTEXT != queries:
        raise ValueError("windowed affinity needs whole 64-query contexts")
    uniq, inverse = torch.unique(selected, return_inverse=True)
    n = int(uniq.numel())
    blocks = inverse.reshape(contexts, core.CONTEXT, width)
    matrix = torch.zeros(n * n, dtype=torch.int32)
    chunk = 64
    for d in range(window + 1):
        if d >= core.CONTEXT:
            break
        for start in range(0, contexts, chunk):
            part = blocks[start : start + chunk]
            a = part[:, d:, :]  # queries t = d..63
            b = part[:, : core.CONTEXT - d, :]  # queries u = t - d
            i = a.unsqueeze(3)  # [c, t, 8, 1]
            j = b.unsqueeze(2)  # [c, t, 1, 8]
            keep = (i != j).reshape(-1)
            keys = (i * n + j).expand(-1, -1, width, width).reshape(-1)[keep]
            swapped = (j * n + i).expand(-1, -1, width, width).reshape(-1)[keep]
            ones = torch.ones(keys.numel(), dtype=torch.int32)
            matrix.index_add_(0, keys, ones)
            matrix.index_add_(0, swapped, ones)
    return _adjacency_from_matrix(matrix, uniq, n)


def group_affinity(adj: Adjacency, group_of: Sequence[int]) -> Adjacency:
    """Affinity between groups: the sum of A between their slots (i and j in different groups)."""
    out: Adjacency = {}
    for i, row in adj.items():
        gi = group_of[i]
        for j, value in row.items():
            gj = group_of[j]
            if gi != gj:
                bucket = out.setdefault(gi, {})
                bucket[gj] = bucket.get(gj, 0) + value
    return out


# --- step 1: greedy page fill
def greedy_pages(
    slots: Sequence[int], rows_per_page: int, f: Sequence[int], adj: Adjacency
) -> list[list[int]]:
    """Greedy page fill (section 4 step 1) over the set ``slots``.

    A page starts with the unplaced slot of highest f (ties: lowest ID). The score vector starts as
    that slot's row of A; the next row is the unplaced slot with the highest score (ties: higher f,
    then lowest ID) and its row of A is added to the scores. Slots with score zero are all tied at
    zero, so when no unplaced slot has a positive score the hottest unplaced slot is taken.
    Pages are in creation order, rows in the order added.
    """
    members = set(slots)
    order = sorted(members, key=lambda s: (-f[s], s))
    placed: set[int] = set()
    pointer = 0
    pages: list[list[int]] = []
    total = len(order)
    while len(placed) < total:
        while order[pointer] in placed:
            pointer += 1
        seed = order[pointer]
        placed.add(seed)
        page = [seed]
        score: dict[int, int] = {}
        for j, value in adj.get(seed, {}).items():
            if j in members and j not in placed:
                score[j] = score.get(j, 0) + value
        while len(page) < rows_per_page and len(placed) < total:
            if score:
                nxt = max(score.items(), key=lambda kv: (kv[1], f[kv[0]], -kv[0]))[0]
                del score[nxt]
            else:
                while order[pointer] in placed:
                    pointer += 1
                nxt = order[pointer]
            placed.add(nxt)
            page.append(nxt)
            for j, value in adj.get(nxt, {}).items():
                if j in members and j not in placed:
                    score[j] = score.get(j, 0) + value
        pages.append(page)
    return pages


def within_page_affinity(pages: Sequence[Sequence[int]], adj: Adjacency) -> int:
    """Total within-page affinity: the sum of A over unordered pairs on the same page."""
    total = 0
    for page in pages:
        for a in range(len(page)):
            row = adj.get(page[a])
            if row:
                for b in range(a + 1, len(page)):
                    total += row.get(page[b], 0)
    return total


# --- step 2: bounded swap refinement
def refine_pages(
    pages: list[list[int]],
    adj: Adjacency,
    f: Sequence[int],
    *,
    group_of: Sequence[int] | None = None,
    max_passes: int = core.MAX_PASSES,
) -> tuple[list[list[int]], dict[str, Any]]:
    """Bounded swap refinement (section 4 step 2), applied to a copy of ``pages``.

    Visit slots with at least one nonzero affinity in order of descending f (ties: slot ID). For
    slot x on page P consider swapping it with any slot y on another page Q that contains at least
    one slot with nonzero affinity to x; the gain is the change in total within-page affinity,
    ``wxQ + wyP - wxP - wyQ - 2 A[x][y]`` (wuV = affinity of u to the other slots on page V). Make
    the single best strictly positive swap for x (ties: lowest page number Q, then lowest slot ID
    y). A swap exchanges the *positions*: y takes the position x held in P, x the position y held
    in Q. Passes repeat until one makes no swap or ``max_passes`` are done. With ``group_of`` every
    page holds slots of one group and a swap partner must lie in x's group.

    Equal-gain partners without any affinity (slots absent from ``adj``) are interchangeable except
    for the lowest-ID rule, so only the lowest-ID such slot of each page is evaluated.
    """
    pages = [list(page) for page in pages]
    where: dict[int, int] = {}
    for index, page in enumerate(pages):
        for slot in page:
            where[slot] = index
    wp: dict[int, dict[int, int]] = {}
    for s, row in adj.items():
        w: dict[int, int] = {}
        for z, value in row.items():
            page_z = where[z]
            w[page_z] = w.get(page_z, 0) + value
        wp[s] = w
    active = sorted(adj, key=lambda s: (-f[s], s))
    within_before = within_page_affinity(pages, adj)
    inactive_cache: dict[int, int | None] = {}

    def lowest_inactive(q: int) -> int | None:
        if q not in inactive_cache:
            free = [s for s in pages[q] if s not in adj]
            inactive_cache[q] = min(free) if free else None
        return inactive_cache[q]

    swaps = passes = 0
    converged = False
    while passes < max_passes:
        passes += 1
        made = 0
        for x in active:
            p = where[x]
            wx = wp[x]
            ax = adj[x]
            wxp = wx.get(p, 0)
            gx = None if group_of is None else group_of[x]
            best: tuple[int, int, int] | None = None  # (gain, -Q, -y)
            for q, wxq in wx.items():
                if q == p or wxq <= 0:
                    continue
                if gx is not None and group_of is not None and group_of[pages[q][0]] != gx:
                    continue
                candidates = [y for y in pages[q] if y in adj]
                free = lowest_inactive(q)
                if free is not None:
                    candidates.append(free)
                for y in candidates:
                    wy = wp.get(y)
                    if wy is None:
                        gain = wxq - wxp
                    else:
                        gain = wxq - 2 * ax.get(y, 0) + wy.get(p, 0) - wxp - wy.get(q, 0)
                    if gain > 0:
                        key = (gain, -q, -y)
                        if best is None or key > best:
                            best = key
            if best is None:
                continue
            q, y = -best[1], -best[2]
            ix, iy = pages[p].index(x), pages[q].index(y)
            pages[p][ix], pages[q][iy] = y, x
            where[x], where[y] = q, p
            inactive_cache.pop(p, None)
            inactive_cache.pop(q, None)
            for z, value in ax.items():
                w = wp[z]
                w[p] -= value
                if not w[p]:
                    del w[p]
                w[q] = w.get(q, 0) + value
            for z, value in adj.get(y, {}).items():
                w = wp[z]
                w[q] -= value
                if not w[q]:
                    del w[q]
                w[p] = w.get(p, 0) + value
            made += 1
            swaps += 1
        if not made:
            converged = True
            break
    info = {
        "passes": passes,
        "swaps": swaps,
        "converged": converged,
        "within_page_affinity_before": within_before,
        "within_page_affinity_after": within_page_affinity(pages, adj),
    }
    return pages, info


# --- layouts
def positions_of(order: Sequence[int]) -> list[int]:
    positions = [-1] * core.SLOTS
    for position, slot in enumerate(order):
        positions[slot] = position
    return positions


def layout_from_pages(pages: Sequence[Sequence[int]]) -> list[int]:
    order = [slot for page in pages for slot in page]
    if sorted(order) != list(range(core.SLOTS)):
        raise core.StopError("a layout is not a permutation of 0..4095")
    return order


def coax_pages(
    rows_per_page: int,
    f: Sequence[int],
    adj: Adjacency,
    *,
    refine: bool,
) -> tuple[list[list[int]], dict[str, Any]]:
    """L-COAX family over all 4,096 slots (steps 1 and 2, or step 1 alone)."""
    pages = greedy_pages(range(core.SLOTS), rows_per_page, f, adj)
    return _maybe_refine(pages, f, adj, None, refine)


def _maybe_refine(
    pages: list[list[int]],
    f: Sequence[int],
    adj: Adjacency,
    group_of: Sequence[int] | None,
    refine: bool,
) -> tuple[list[list[int]], dict[str, Any]]:
    if not refine:
        return pages, {
            "passes": 0,
            "swaps": 0,
            "converged": True,
            "within_page_affinity_before": within_page_affinity(pages, adj),
            "within_page_affinity_after": within_page_affinity(pages, adj),
        }
    return refine_pages(pages, adj, f, group_of=group_of)


def group_order(groups: Sequence[Sequence[int]], f: Sequence[int]) -> list[int]:
    """Groups (branches or partition groups) by descending total calibration count, ties by lowest
    group index."""
    totals = [sum(f[s] for s in g) for g in groups]
    return sorted(range(len(groups)), key=lambda g: (-totals[g], g))


def group_coax_pages(
    groups: Sequence[Sequence[int]],
    rows_per_page: int,
    f: Sequence[int],
    adj: Adjacency,
    *,
    refine: bool,
) -> tuple[list[list[int]], dict[str, Any]]:
    """L-BCOAX / L-PCOAX family: groups ordered by descending total count; steps 1 and 2 inside each
    group with swaps restricted to the group; for R = 512 (a page of two groups) the two steps are
    applied to the groups themselves and the rows inside a group keep the order of the R = 256
    construction (one 256-row greedy page per group)."""
    group_of = [-1] * core.SLOTS
    for g, members in enumerate(groups):
        for slot in members:
            group_of[slot] = g
    if rows_per_page > core.PER_BRANCH:
        per_page = rows_per_page // core.PER_BRANCH
        totals = [sum(f[s] for s in g) for g in groups]
        adj_g = group_affinity(adj, group_of)
        unit_pages = greedy_pages(range(len(groups)), per_page, totals, adj_g)
        unit_pages, info = _maybe_refine(unit_pages, totals, adj_g, None, refine)
        rows_in_group = {
            g: [s for page in greedy_pages(groups[g], core.PER_BRANCH, f, adj) for s in page]
            for g in range(len(groups))
        }
        pages = [[s for g in unit for s in rows_in_group[g]] for unit in unit_pages]
        return pages, info
    pages = []
    for g in group_order(groups, f):
        pages += greedy_pages(groups[g], rows_per_page, f, adj)
    if not refine:
        return _maybe_refine(pages, f, adj, group_of, False)
    return refine_pages(pages, adj, f, group_of=group_of)


# --- partitions
def partition_shuffled(seed: int) -> list[int]:
    shuffled = list(range(core.SLOTS))
    random.Random(seed).shuffle(shuffled)
    return shuffled


def partition_groups(seed: int) -> list[list[int]]:
    shuffled = partition_shuffled(seed)
    return [shuffled[g * core.PER_BRANCH : (g + 1) * core.PER_BRANCH] for g in range(core.BRANCHES)]


def branch_groups() -> list[list[int]]:
    return [
        list(range(b * core.PER_BRANCH, (b + 1) * core.PER_BRANCH)) for b in range(core.BRANCHES)
    ]


def partition_hash(seed: int) -> str:
    shuffled = partition_shuffled(seed)
    return sha256(struct.pack(f"<{len(shuffled)}H", *shuffled))


def verify_partitions() -> dict[str, Any]:
    """The five registered partitions: hashes must match (else the study stops), each is 16
    disjoint groups of 256 covering every slot, and they are pairwise different."""
    sets: dict[int, frozenset[frozenset[int]]] = {}
    for seed in core.PARTITION_SEEDS:
        digest = partition_hash(seed)
        if digest != core.PARTITION_SHA256[seed]:
            raise core.StopError(f"partition {seed} hash {digest} differs from the registered one")
        groups = partition_groups(seed)
        flat = sorted(s for g in groups for s in g)
        if (
            len(groups) != core.BRANCHES
            or any(len(g) != core.PER_BRANCH for g in groups)
            or flat != list(range(core.SLOTS))
        ):
            raise core.StopError(f"partition {seed} is not 16 disjoint groups of 256")
        sets[seed] = frozenset(frozenset(g) for g in groups)
    if len(set(sets.values())) != len(sets):
        raise core.StopError("two registered partitions are identical")
    return {str(seed): partition_hash(seed) for seed in core.PARTITION_SEEDS}


# --- the checkpoint layout set
@dataclass
class BuiltLayout:
    name: str
    rows: int | None  # None for layouts that do not depend on R
    order: list[int]
    info: dict[str, Any] = field(default_factory=dict)

    def key(self) -> str:
        return self.name if self.rows is None else core.layout_key(self.name, self.rows)


def _check_layout(layout: BuiltLayout, groups: Sequence[Sequence[int]] | None) -> None:
    if sorted(layout.order) != list(range(core.SLOTS)):
        raise core.StopError(f"layout {layout.key()} is not a permutation of 0..4095")
    if groups is not None:
        for g, members in enumerate(groups):
            wanted = set(members)
            places = sorted(p for p, s in enumerate(layout.order) if s in wanted)
            if places[-1] - places[0] + 1 != len(members):
                raise core.StopError(f"layout {layout.key()} does not keep group {g} contiguous")


def build_layouts(
    calibration: CalibrationTrace,
    *,
    rows_list: Sequence[int] = core.RS,
    check: bool = True,
) -> tuple[list[BuiltLayout], dict[str, Any]]:
    """Every layout of ADR-0014 section 4 for one checkpoint, from its calibration trace only.

    Order of the result: the R-independent layouts, then for each R the co-access layouts in
    registered order. Each co-access layout is one deterministic construction (no restarts, no
    choice among candidates). Also returns metadata: the calibration null streams' hashes (seeds
    91311-91313; only the first replicate enters L-NCOAX) and the affinity sizes.
    """
    cal = require_calibration(calibration)
    kind, label = cal.kind, cal.label
    tree = core.is_tree(kind)
    counts = cal.counts()
    pair, label_kind = core.parse_label(label)
    if label_kind != kind:
        raise ValueError("calibration trace kind does not match its label")
    index = core.cell_index(pair, kind)
    from . import p7a_core as a_core

    out: list[BuiltLayout] = []
    freq_positions = a_core.layout_freq(counts)
    bfreq_positions = a_core.layout_bfreq(counts) if tree else None

    def order_of(positions: list[int]) -> list[int]:
        order = [0] * core.SLOTS
        for slot, position in enumerate(positions):
            order[position] = slot
        return order

    out.append(BuiltLayout(core.L_ID, None, list(range(core.SLOTS))))
    for seed, name in zip(core.RAND_SEEDS, core.L_RANDS, strict=True):
        out.append(BuiltLayout(name, None, order_of(a_core.layout_rand(seed))))
    out.append(BuiltLayout(core.L_FREQ, None, order_of(freq_positions)))
    if bfreq_positions is not None:
        out.append(BuiltLayout(core.L_BFREQ, None, order_of(bfreq_positions)))

    adj = pair_affinity(cal.selected)
    adj8 = window_affinity(cal.selected)
    null_list, null_info = core.null_streams(counts, core.CAL_NULL_SEEDS, index)
    adj_null = pair_affinity(null_list[0])
    branches = branch_groups()
    partitions = {
        name: partition_groups(seed)
        for name, seed in zip(core.L_PCOAX, core.PARTITION_SEEDS, strict=True)
    }

    for rows in rows_list:
        plan: list[tuple[str, Adjacency, bool, Sequence[Sequence[int]] | None]] = [
            (core.L_COAX, adj, True, None),
            (core.L_NCOAX, adj_null, True, None),
            (core.L_COAX8, adj8, True, None),
            (core.L_COAXG, adj, False, None),
        ]
        plan += [(name, adj, True, groups) for name, groups in partitions.items()]
        if tree:
            plan += [
                (core.L_BCOAX, adj, True, branches),
                (core.L_BCOAX8, adj8, True, branches),
                (core.L_BCOAXG, adj, False, branches),
            ]
        for name, affinity, refine, groups in plan:
            if groups is None:
                pages, info = coax_pages(rows, counts, affinity, refine=refine)
            else:
                pages, info = group_coax_pages(groups, rows, counts, affinity, refine=refine)
            layout = BuiltLayout(name, rows, layout_from_pages(pages), info)
            if check:
                _check_layout(layout, groups)
            out.append(layout)
    meta = {
        "calibration_counts_sha256": core.counts_sha256(counts),
        "calibration_null_streams": [
            {k: info[k] for k in ("replicate_seed", "generator_seed", "stream_sha256")}
            for info in null_info
        ],
        "l_ncoax_uses_replicate_seed": core.CAL_NULL_SEEDS[0],
        "affinity_nonzero_entries": {
            "A": sum(len(r) for r in adj.values()),
            "A8": sum(len(r) for r in adj8.values()),
            "A_null": sum(len(r) for r in adj_null.values()),
        },
        "unique_selected_slots": sum(1 for c in counts if c),
    }
    return out, meta


def split_half_layouts(
    calibration: CalibrationTrace, half: int, names: Sequence[str], rows: int
) -> dict[str, list[int]]:
    """Criterion layouts refitted on one half of the calibration contexts (half 0: contexts
    0..255, half 1: 256..511), same algorithm. Used for split-half stability (calibration only)."""
    cal = require_calibration(calibration)
    n = cal.selected.shape[0] // 2
    sel = cal.selected[:n] if half == 0 else cal.selected[n:]
    f = torch.bincount(sel.flatten(), minlength=core.SLOTS).tolist()
    adj = pair_affinity(sel)
    out: dict[str, list[int]] = {}
    for name in names:
        if name == core.L_FREQ:
            out[name] = sorted(range(core.SLOTS), key=lambda s: (-f[s], s))
        elif name == core.L_COAX:
            out[name] = layout_from_pages(coax_pages(rows, f, adj, refine=True)[0])
        elif name == core.L_BCOAX:
            out[name] = layout_from_pages(
                group_coax_pages(branch_groups(), rows, f, adj, refine=True)[0]
            )
        elif name in core.L_PCOAX:
            seed = core.PARTITION_SEEDS[core.L_PCOAX.index(name)]
            out[name] = layout_from_pages(
                group_coax_pages(partition_groups(seed), rows, f, adj, refine=True)[0]
            )
        else:
            raise ValueError(f"no split-half construction for {name}")
    return out


# --- on-disk layout files
def write_layout_file(path: Path, layouts: list[BuiltLayout]) -> list[dict[str, Any]]:
    """One binary file per checkpoint: each layout as 4,096 little-endian int16 slot IDs in position
    order (``order``), concatenated. Returns the index (entry offsets) and per-layout hashes."""
    index: list[dict[str, Any]] = []
    blob = bytearray()
    for n, layout in enumerate(layouts):
        blob += struct.pack(f"<{core.SLOTS}h", *layout.order)
        index.append(
            {
                "name": layout.name,
                "rows": layout.rows,
                "entry": n,
                "bytes_offset": n * core.SLOTS * 2,
                "info": layout.info,
            }
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(bytes(blob))
    return index


def read_layout_file(path: Path, index: list[dict[str, Any]]) -> dict[str, list[int]]:
    data = path.read_bytes()
    if len(data) != len(index) * core.SLOTS * 2:
        raise core.StopError(f"layout file {path.name} has an unexpected length")
    out: dict[str, list[int]] = {}
    for entry in index:
        start = entry["bytes_offset"]
        values = struct.unpack(f"<{core.SLOTS}h", data[start : start + core.SLOTS * 2])
        key = (
            entry["name"]
            if entry["rows"] is None
            else core.layout_key(entry["name"], entry["rows"])
        )
        out[key] = list(values)
    return out


def hash_table(layouts: list[BuiltLayout], rows_list: Sequence[int] = core.RS) -> dict[str, str]:
    """Canonical hash of every (layout, R): R-independent layouts are hashed at each R."""
    table: dict[str, str] = {}
    for layout in layouts:
        if layout.rows is None:
            for rows in rows_list:
                table[core.layout_key(layout.name, rows)] = core.canonical_hash(layout.order, rows)
        else:
            table[layout.key()] = core.canonical_hash(layout.order, layout.rows)
    return table


def layout_file_sha256(path: Path) -> str:
    return file_sha256(path)
