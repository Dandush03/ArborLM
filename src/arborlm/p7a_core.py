"""P7-A shared definitions: registry, trace files, integrity checks, layouts, streams, closed form.

Specification: docs/decisions/ADR-0013-p7a-storage-page-locality.md (HUMAN-APPROVED, revision 2,
with the section 14 clarifications). Nothing here chooses a scientific value: every constant below
is copied from that ADR. Pure integer and tensor bookkeeping; no model is imported at module level.

Status: implementation self-checked only. Not independent review, not Astra validation.
"""

import random
import struct
import sys
from fractions import Fraction
from functools import cache
from math import comb
from pathlib import Path
from typing import Any

import torch
from torch import Tensor

from .io import file_sha256, sha256
from .p5_config import FIXED as FIXED
from .p5_config import FLAT as FLAT
from .p5_config import LEARNED, MEMORIES
from .p6_common import Pair, pair_index, pairs

SPEC = "docs/decisions/ADR-0013-p7a-storage-page-locality.md"
STUDY = "P7-A"
FAMILY = "P7A_STORAGE_PAGE_LOCALITY"
SCHEMA_TRACE = "P7A-trace-v1"
SCHEMA_SIM = "P7A-simulation-v1"
SCHEMA_ANALYSIS = "P7A-analysis-v1"
P5_RESULTS = Path("results/p5-2026-11-13")

# --- registered constants (ADR-0013 sections 2-5, 7, 10, 14) -----------------------------------
SLOTS, BRANCHES, PER_BRANCH, TOP, TREE_VISIT = 4096, 16, 256, 8, 2
CONTEXT, CONTEXTS = 64, 512
QUERIES = CONTEXT * CONTEXTS  # 32,768
WARM_QUERIES = QUERIES // 2  # clarification 4: queries 0-16,383 warm, 16,384-32,767 counted
COUNTED_QUERIES = QUERIES - WARM_QUERIES
RS = (1, 2, 8, 32, 128, 512)
CS = (8, 16, 32, 64, 128)
RAND_SEEDS = (91101, 91102, 91103)
ORDER_SHUFFLE_SEED = 91201
CONTEXT_SHUFFLE_SEED = 91202
FM_SEEDS = (91301, 91302, 91303)
BOOTSTRAP_SEED = 91401
INDEPENDENT_SELECTION_SEED = 91501
BOOTSTRAP_RESAMPLES = 1000
PRIMARY_R, PRIMARY_C = 2, 32
PRIMARY = {"R": PRIMARY_R, "C": PRIMARY_C, "layout": "L-FREQ", "stream": "actual"}
RATIO_LIMIT = Fraction(4, 5)
FLAT_FLOOR = Fraction(1, 20)
TREE_FLOOR = Fraction(1, 100)
MIN_CELLS, MIN_PARENTS = 22, 8
CAL_START, CAL_END = 2048, 2560  # training-pool ranks used only to fit layouts
EVAL_RANKS = (2048, 2560)
CUMULATIVE_POINTS = (64, 128, 256, 512, 1024, 2048, 4096, 8192, 16384, 32768)  # implementer set
PAGE_BYTES_FOR_R = {1: 4096, 2: 4096, 8: 4096, 32: 4096, 128: 16384, 512: 65536}
KEY_ROW_BYTES = 64
# Caps (section 10). Seconds of active worker time unless stated.
TRACE_CAP, SIM_CAP, COMBINED_CAP = 900.0, 3600.0, 4500.0
KINDS = MEMORIES  # ("flat", "fixed_tree", "learned_tree")
TREE_KINDS = (FIXED, LEARNED)

STREAM_ACTUAL = "actual"
STREAM_ORDER = "order_shuffled"
STREAM_CONTEXT = "context_shuffled"
STREAMS_FM = tuple(f"freq_matched_{i}" for i in (1, 2, 3))
STREAMS_OTHER = (STREAM_ORDER, *STREAMS_FM, STREAM_CONTEXT)
LAYOUT_ID, LAYOUT_FREQ, LAYOUT_BFREQ = "L-ID", "L-FREQ", "L-BFREQ"
LAYOUTS_RAND = tuple(f"L-RAND-{s}" for s in RAND_SEEDS)
LAYOUTS_FLAT = (LAYOUT_ID, *LAYOUTS_RAND, LAYOUT_FREQ)
LAYOUTS_TREE = (*LAYOUTS_FLAT, LAYOUT_BFREQ)
LAYOUTS_OTHER = (LAYOUT_ID, LAYOUT_FREQ)
KEY_LAYOUTS = (LAYOUT_ID, *LAYOUTS_RAND)

KNOWN_LIMITS = (
    "Every number is a count under a page model; none is a device measurement, latency, "
    "throughput or timing. A page-read count is not a time.",
    "R = 1, 2 and 8 are hypothetical row sizes that relabel bytes per row; they change no "
    "selection and no weight.",
    "No NVMe experiment on the existing checkpoints is proposed under any outcome (ADR-0013 "
    "section 2 and 8).",
    "Contexts are unrelated 64-byte teacher-forced windows; temporal structure exists only within "
    "a context's 64 queries.",
    "Frequency packing is not the best possible flat layout; no co-access clustering, no "
    "Belady caching, no key-clustered flat layout.",
    "Consistency counts over 27 pairs describe robustness to training randomness only; they are "
    "not significance tests.",
)


class TraceIntegrityError(ValueError):
    """A section 9 trace-integrity violation: a hard stop."""


class InvariantError(ValueError):
    """A section 9 simulator-invariant violation: a hard stop."""


# --- registry -----------------------------------------------------------------------------------
def registered_checkpoints() -> list[tuple[Pair, str]]:
    """The 81 final checkpoints in registered order: parent/seed ascending; flat, fixed, learned."""
    return [(pair, kind) for pair in pairs() for kind in KINDS]


def cell_index(pair: Pair, kind: str) -> int:
    return pair_index(pair) * 3 + KINDS.index(kind)


def cell_label(pair: Pair, kind: str) -> str:
    b, o, s = pair
    return f"b{b}-o{o}-{kind}-s{s}"


def parse_label(label: str) -> tuple[Pair, str]:
    for pair, kind in registered_checkpoints():
        if cell_label(pair, kind) == label:
            return pair, kind
    raise ValueError(f"not a registered P7-A checkpoint label: {label!r}")


def parent_of(pair: Pair) -> tuple[int, int]:
    return pair[0], pair[1]


def layouts_for(kind: str) -> tuple[str, ...]:
    return LAYOUTS_FLAT if kind == FLAT else LAYOUTS_TREE


def source_hashes(root: Path | None = None) -> dict[str, str]:
    base = root or Path(__file__).resolve().parent
    return {f"src/arborlm/{p.name}": file_sha256(p) for p in sorted(base.glob("p7a_*.py"))}


def spec_sha256(repo: Path | None = None) -> str:
    return file_sha256((repo or Path.cwd()) / SPEC)


# --- trace files ---------------------------------------------------------------------------------
def _pack(tensor: Tensor, code: str) -> bytes:
    values = tensor.reshape(-1).tolist()
    return struct.pack(f"<{len(values)}{code}", *values)


def _unpack(data: bytes, code: str, shape: tuple[int, ...]) -> Tensor:
    size = struct.calcsize(code)
    count = len(data) // size
    if count * size != len(data):
        raise TraceIntegrityError("trace file length is not a whole number of elements")
    dtype = {"h": torch.int16, "b": torch.int8}[code]
    if sys.byteorder == "little":
        tensor = torch.frombuffer(bytearray(data), dtype=dtype).clone()
    else:  # pragma: no cover - the registered platforms are little endian
        tensor = torch.tensor(struct.unpack(f"<{count}{code}", data), dtype=dtype)
    if tensor.numel() != int(torch.tensor(shape).prod()):
        raise TraceIntegrityError(f"trace file has {tensor.numel()} elements, expected {shape}")
    return tensor.reshape(shape).to(torch.int64)


def write_trace(
    directory: Path,
    prefix: str,
    selected: Tensor,
    branches: Tensor | None,
    queries: int = QUERIES,
) -> dict[str, Any]:
    """Write one trace (little-endian binary) and return its compact record.

    ``selected`` is int16 [32768, 8] on disk, ``branches`` int8 [32768, 2] (trees only).
    """
    directory.mkdir(parents=True, exist_ok=True)
    record: dict[str, Any] = {}
    parts = [("selected", selected, "h", "int16", TOP)]
    if branches is not None:
        parts.append(("branches", branches, "b", "int8", TREE_VISIT))
    for name, tensor, code, dtype, width in parts:
        shape = (queries, width)
        if tuple(tensor.shape) != shape:
            raise TraceIntegrityError(f"{prefix}_{name} has shape {tuple(tensor.shape)}")
        path = directory / f"{prefix}_{name}.{dtype}.bin"
        path.write_bytes(_pack(tensor, code))
        record[name] = {
            "file": path.name,
            "dtype": "<i2" if code == "h" else "|i1",
            "layout": "little-endian signed integers, C order, no header (numpy dtype string)",
            "shape": list(shape),
            "sha256": file_sha256(path),
        }
    if branches is None:
        record["branches"] = None
    return record


def read_trace(
    directory: Path, prefix: str, record: dict[str, Any]
) -> tuple[Tensor, Tensor | None]:
    """Read a trace back, verifying the recorded SHA-256 of each file first."""
    out: list[Tensor | None] = []
    for name, code in (("selected", "h"), ("branches", "b")):
        entry = record.get(name)
        if entry is None:
            out.append(None)
            continue
        path = directory / entry["file"]
        if not path.name.startswith(prefix):
            raise TraceIntegrityError(f"unexpected trace file {path.name} for {prefix}")
        if file_sha256(path) != entry["sha256"]:
            raise TraceIntegrityError(f"trace file hash differs from its record: {path.name}")
        out.append(_unpack(path.read_bytes(), code, tuple(entry["shape"])))
    selected = out[0]
    if selected is None:
        raise TraceIntegrityError("trace record has no selected-slot file")
    return selected, out[1]


def check_trace(
    selected: Tensor,
    branches: Tensor | None,
    kind: str,
    *,
    recorded: dict[str, Any] | None = None,
    queries: int = QUERIES,
) -> dict[str, Any]:
    """Section 9 trace-integrity checks; raises ``TraceIntegrityError``.

    IDs in range and distinct within a query; for trees the visited branch IDs are in range and
    distinct and every selected slot lies in a visited branch; when ``recorded`` (the P5
    ``final.retrieval`` record) is given, the unique-selected-slot count and per-slot histogram
    must be reproduced exactly.
    """
    if tuple(selected.shape) != (queries, TOP):
        raise TraceIntegrityError(f"selected trace has shape {tuple(selected.shape)}")
    selected = selected.to(torch.int64)
    if int(selected.min()) < 0 or int(selected.max()) >= SLOTS:
        raise TraceIntegrityError("selected slot ID out of range")
    ordered = selected.sort(dim=1).values
    if bool((ordered[:, 1:] == ordered[:, :-1]).any()):
        raise TraceIntegrityError("duplicate slot ID within a query")
    tree = kind != FLAT
    if tree != (branches is not None):
        raise TraceIntegrityError("branch trace presence does not match the architecture")
    if branches is not None:
        branches = branches.to(torch.int64)
        if tuple(branches.shape) != (queries, TREE_VISIT):
            raise TraceIntegrityError(f"branch trace has shape {tuple(branches.shape)}")
        if int(branches.min()) < 0 or int(branches.max()) >= BRANCHES:
            raise TraceIntegrityError("visited branch ID out of range")
        if bool((branches[:, 0] == branches[:, 1]).any()):
            raise TraceIntegrityError("a query visited the same branch twice")
        own = selected // PER_BRANCH
        inside = (own == branches[:, :1]) | (own == branches[:, 1:2])
        if not bool(inside.all()):
            raise TraceIntegrityError("a selected slot lies outside the visited branches")
    counts = torch.bincount(selected.flatten(), minlength=SLOTS)
    if recorded is not None:
        if counts.tolist() != recorded["selected_slot_counts"]:
            raise TraceIntegrityError("selected-slot histogram differs from the recorded P5 one")
        if int((counts > 0).sum()) != recorded["unique_selected_slots"]:
            raise TraceIntegrityError("unique selected slots differ from the recorded P5 count")
    return {
        "queries": queries,
        "unique_selected_slots": int((counts > 0).sum()),
        "histogram_matches_p5": recorded is not None,
    }


def selection_counts(selected: Tensor) -> list[int]:
    return torch.bincount(selected.to(torch.int64).flatten(), minlength=SLOTS).tolist()


# --- layouts (section 4) --------------------------------------------------------------------------
def is_permutation(positions: list[int]) -> bool:
    return len(positions) == SLOTS and sorted(positions) == list(range(SLOTS))


def layout_id() -> list[int]:
    return list(range(SLOTS))


def layout_rand(seed: int) -> list[int]:
    """Slot s sits at position ``randperm(4096)[s]`` (generator seeded ``seed``); every checkpoint
    receives the same permutation for a seed (clarification 3)."""
    generator = torch.Generator().manual_seed(seed)
    return torch.randperm(SLOTS, generator=generator).tolist()


def layout_freq(calibration_counts: list[int]) -> list[int]:
    """Position of each slot when slots are sorted by descending calibration count, ties by
    ascending slot ID. Depends on the calibration counts only."""
    order = sorted(range(SLOTS), key=lambda slot: (-calibration_counts[slot], slot))
    positions = [0] * SLOTS
    for position, slot in enumerate(order):
        positions[slot] = position
    return positions


def layout_bfreq(calibration_counts: list[int]) -> list[int]:
    """Branches contiguous in branch-ID order; inside each branch slots by descending calibration
    count, ties by ascending slot ID. Depends on the calibration counts only."""
    positions = [0] * SLOTS
    for branch in range(BRANCHES):
        base = branch * PER_BRANCH
        order = sorted(range(base, base + PER_BRANCH), key=lambda s: (-calibration_counts[s], s))
        for rank, slot in enumerate(order):
            positions[slot] = base + rank
    return positions


def build_layouts(kind: str, calibration_counts: list[int]) -> dict[str, list[int]]:
    layouts: dict[str, list[int]] = {LAYOUT_ID: layout_id()}
    for seed, name in zip(RAND_SEEDS, LAYOUTS_RAND, strict=True):
        layouts[name] = layout_rand(seed)
    layouts[LAYOUT_FREQ] = layout_freq(calibration_counts)
    if kind != FLAT:
        layouts[LAYOUT_BFREQ] = layout_bfreq(calibration_counts)
    for name, positions in layouts.items():
        if not is_permutation(positions):
            raise InvariantError(f"layout {name} is not a permutation of 0..4095")
    if kind != FLAT:
        for slot in range(SLOTS):
            if layouts[LAYOUT_BFREQ][slot] // PER_BRANCH != slot // PER_BRANCH:
                raise InvariantError("L-BFREQ does not preserve branch membership")
    return layouts


# --- streams --------------------------------------------------------------------------------------
def order_permutation(queries: int = QUERIES) -> list[int]:
    generator = torch.Generator().manual_seed(ORDER_SHUFFLE_SEED)
    return torch.randperm(queries, generator=generator).tolist()


def context_permutation(contexts: int = CONTEXTS) -> list[int]:
    generator = torch.Generator().manual_seed(CONTEXT_SHUFFLE_SEED)
    return torch.randperm(contexts, generator=generator).tolist()


def query_order(stream: str, queries: int = QUERIES) -> list[int]:
    """Indices into the actual stream that make up a permutation ``stream``."""
    if stream == STREAM_ORDER:
        return order_permutation(queries)
    if stream == STREAM_CONTEXT:
        return [
            c * CONTEXT + i for c in context_permutation(queries // CONTEXT) for i in range(CONTEXT)
        ]
    raise ValueError(f"not a permutation stream: {stream}")


def fm_generator_seed(replicate_seed: int, index: int) -> int:
    """ADR-0013 section 14 item 8: seed = s * 1000 + cell_index."""
    return replicate_seed * 1000 + index


def _deal_and_repair(
    counts: list[int], generator: random.Random, queries: int, top: int
) -> tuple[list[list[int]], int]:
    """Item 8 steps 1-3. Returns the dealt-and-repaired rows (before the final query permutation)
    and the number of swaps.

    1. All occurrences in slot-ID order (slot i repeated ``counts[i]`` times), shuffled with
       ``generator.shuffle``.
    2. Dealt into ``queries`` rows of ``top`` consecutive entries.
    3. For q ascending, while row q holds a duplicated slot x (the later position of the first
       duplicated pair): scan r = q+1, q+2, ... cyclically for the first row that does not contain
       x and has an entry y not present in row q (lowest position); swap x and y. Every slot count
       is preserved and each swap removes one duplicate.
    """
    occurrences = [slot for slot, count in enumerate(counts) for _ in range(count)]
    generator.shuffle(occurrences)
    rows = [occurrences[i * top : (i + 1) * top] for i in range(queries)]
    swaps = 0
    for q in range(queries):
        row = rows[q]
        while len(set(row)) < top:
            seen: set[int] = set()
            position = -1
            for j, slot in enumerate(row):
                if slot in seen:
                    position = j
                    break
                seen.add(slot)
            x = row[position]
            mine = set(row)
            for step in range(1, queries):
                other = rows[(q + step) % queries]
                if x in other:
                    continue
                k = next((k for k, slot in enumerate(other) if slot not in mine), -1)
                if k >= 0:
                    row[position], other[k] = other[k], row[position]
                    swaps += 1
                    break
            else:
                raise InvariantError(
                    f"count-preserving repair found no swap for slot {x} (row {q})"
                )
    return rows, swaps


def frequency_matched_detail(
    counts: list[int],
    replicate_seed: int,
    index: int,
    *,
    queries: int = QUERIES,
    top: int = TOP,
) -> tuple[Tensor, dict[str, Any]]:
    """The exact count-preserving frequency-matched stream (ADR-0013 section 14 item 8) and a
    compact record of how it was generated.

    ``counts`` are the checkpoint's evaluation-trace selection counts. ``g = random.Random(
    replicate_seed * 1000 + index)`` (one generator, used for the step-1 shuffle and then for the
    step-4 permutation of the query indices, in that order). Registered hard-stop check: every
    per-slot count of the result equals ``counts`` exactly and every query holds ``top`` distinct
    slots (``InvariantError`` otherwise). A histogram that no arrangement can realize raises
    ``ValueError`` (a slot with a count above the number of queries, or a wrong total).
    """
    if min(counts, default=0) < 0:
        raise ValueError("a selection count is negative")
    if sum(counts) != top * queries:
        raise ValueError(
            f"counts sum to {sum(counts)} occurrences, expected {top} x {queries} = {top * queries}"
        )
    hottest = max(range(len(counts)), key=counts.__getitem__)
    if counts[hottest] > queries:
        raise ValueError(
            f"slot {hottest} is selected {counts[hottest]} times but there are only {queries} "
            "queries: no arrangement with distinct slots in every query exists"
        )
    seed = fm_generator_seed(replicate_seed, index)
    generator = random.Random(seed)
    rows, swaps = _deal_and_repair(counts, generator, queries, top)
    order = list(range(queries))
    generator.shuffle(order)
    stream = [rows[i] for i in order]
    realized = [0] * len(counts)
    for row in stream:
        if len(set(row)) != top:
            raise InvariantError("frequency-matched stream: a query lacks distinct slots")
        for slot in row:
            realized[slot] += 1
    if realized != counts:
        raise InvariantError("frequency-matched stream: per-slot counts differ from the trace's")
    out = torch.tensor(stream, dtype=torch.int64)
    info = {
        "method": "exact count-preserving (ADR-0013 section 14 item 8)",
        "generator_seed": seed,
        "replicate_seed": replicate_seed,
        "cell_index": index,
        "repair_swaps": swaps,
        "counts_equal_trace": True,
        "distinct_slots_per_query": True,
        "stream_sha256": sha256(_pack(out, "h")),
    }
    return out, info


def frequency_matched(
    counts: list[int],
    replicate_seed: int,
    index: int,
    *,
    queries: int = QUERIES,
    top: int = TOP,
) -> Tensor:
    """The frequency-matched stream as an int64 ``[queries, top]`` tensor (see
    ``frequency_matched_detail``)."""
    return frequency_matched_detail(counts, replicate_seed, index, queries=queries, top=top)[0]


def independent_selection() -> list[str]:
    """ADR-0013 section 14 item 12: for flat, fixed_tree, learned_tree in that order, the first
    three checkpoints in registered order plus three of the remaining 24 drawn with
    ``random.Random(91501).sample`` (one generator shared across the architectures). Within an
    architecture the six labels are listed in registered order."""
    order = [cell_label(p, k) for p, k in registered_checkpoints()]
    generator = random.Random(INDEPENDENT_SELECTION_SEED)
    chosen: list[str] = []
    for kind in KINDS:
        mine = [cell_label(p, k) for p, k in registered_checkpoints() if k == kind]
        extra = generator.sample(mine[3:], 3)
        chosen += mine[:3] + sorted(extra, key=order.index)
    return chosen


# --- uniform closed form (section 5) --------------------------------------------------------------
@cache
def _miss_probability(n: int, m: int, k: int) -> Fraction:
    return Fraction(comb(n - m, k), comb(n, k))


def expected_distinct_pages(page_rows: list[int], k: int = TOP) -> float:
    """``sum_j [1 - C(N - m_j, k) / C(N, k)]`` with ``m_j`` candidate rows on page j (exact
    rational arithmetic, returned as a float); pages with no candidate rows contribute 0."""
    n = sum(page_rows)
    if k > n:
        raise ValueError("cannot draw more rows than candidates")
    total = Fraction(0)
    for m in page_rows:
        if m:
            total += 1 - _miss_probability(n, m, k)
    return float(total)


def uniform_flat(rows_per_page: int) -> float:
    return expected_distinct_pages([rows_per_page] * (SLOTS // rows_per_page), TOP)


def branch_pair_rows_per_page(
    positions: list[int], rows_per_page: int, pair: tuple[int, int]
) -> list[int]:
    """m_j for the 512 candidate rows of two branches under a layout."""
    counts: dict[int, int] = {}
    for branch in pair:
        for slot in range(branch * PER_BRANCH, (branch + 1) * PER_BRANCH):
            page = positions[slot] // rows_per_page
            counts[page] = counts.get(page, 0) + 1
    return list(counts.values())


def pair_key(a: int, b: int) -> tuple[int, int]:
    return (a, b) if a < b else (b, a)
