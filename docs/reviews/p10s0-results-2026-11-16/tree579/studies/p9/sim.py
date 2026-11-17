# ruff: noqa: E501
"""P9 page-cache simulator for general N (package I4): LRU page misses, cache rule, count-preserving
nulls with ADR-0016's identity null, pages per query and cross-query reuse, planted-trace generator and
the key-traffic identity.

Specification: ADR-0017 section 8.4 (simulator, traces, cache rule, E), 9 (synthetic part, D09 sweep,
key traffic). The page model is P7-B's (ADR-0013 / ADR-0014 section 5), re-implemented without the
4,096-slot, 64-query-context and 32,768-query assumptions: value pages only; ``rows`` slots per page;
one cache of C pages; a query is served as a unit (its distinct pages are touched in ascending page
number, tie rule ``asc``, or descending, ``desc``; misses are fetched; then the least recently used
pages not used by the current query are evicted down to C); the first half of the stream warms the
cache, the second half is counted; a first-touch miss is a page never read before in the stream.
``actual_misses`` is the counted CAPACITY miss count (counted misses minus counted first-touch
misses, P8's ``m`` numerator); the counted misses with first touches are kept beside it.

E convention (lead decision after decision 1; P7-B's and P8's): the primary ``e_ratio`` of a layout L is
(actual capacity misses under L) / (mean over the three count-preserving nulls of the capacity misses
under the FREQUENCY layout fitted on the same calibration trace, at the same R, C and tie rule). The
DEGENERATE null-floor test uses that same frequency-layout null denominator (``null_miss_rate`` is that
mean over the counted queries). The older same-layout ratio (nulls simulated under L itself) is kept as
the descriptive field ``e_same_layout`` (with ``null_misses_same_layout`` and
``null_miss_rate_same_layout``); no class ever uses it. Why they differ: the frequency layout packs the
hot slots together, which is what a count-preserving null can exploit, so the frequency-layout null is a
lower (or equal) floor than the null under a layout like identity that spreads the hot slots; the
primary ratio therefore credits a layout for everything it gains over a popularity-only packing, while
the same-layout ratio only measures what is left after shuffling who shares slots with whom under L.

Scope of trained-trace simulation (lead decision): ``simulation_plan`` names, from the registry, which
cells get which simulations; ``simulate_cell`` itself simulates what it is told.

Required before use (ADR 8.4): exact equivalence with P7-B at 4,096 slots on recorded traces:
``p7b_equivalence`` / ``python -m studies.p9.sim equivalence``. Simulated misses are a logical
simulation of an LRU page cache, never storage I/O; the key-traffic result is an arithmetic identity
(ADR 5.2), labelled as such.

Imported unchanged from the frozen code (size-independent): ``arborlm.p7a_core._deal_and_repair`` and
``fm_generator_seed`` (the registered count-preserving generator's body; ``frequency_matched_detail``
itself hashes with int16 and fails above 32,767 slots),
``supplements.p8s.null.precondition_from_counts`` and ``identity_stream`` (ADR-0016 section 3),
``arborlm.p7b_sim.quantiles``. Re-implemented: page sets, the LRU pass (no 64-query contexts, any
query count), pages per query, reuse, nulls for any N and Q, everything below.

Status: implementation self-check only. Not independent review, not Astra validation.
"""

import argparse
import dataclasses
import json
import platform
import random
import struct
import sys
import time
from collections import OrderedDict
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any, NamedTuple

import torch
from torch import Tensor

from arborlm import p7a_core as a_core
from arborlm.io import file_sha256, read_json, sha256, write_json

from . import core
from .core import Cell, Identity, SimRecord, Trace
from .layout import (
    Layout,
    build_layouts,
    frequency_layout,
    group_coaccess_layout,
    sparse_coaccess,
    write_layouts,
)

PageSets = list[tuple[int, ...]]
TOP = 8
CROSS_QUERY_WINDOW = (
    8  # P8's TEMPORAL_WINDOW_QUERIES; the ADR names no window (reported to the lead)
)
RANDOM_PARTITION_SEED = core.DATA_SEEDS[
    "branch_hash"
]  # control layout only; no seed is registered for it
IDENTITY_NULL_METHOD = "single-set identity null (ADR-0016 §3)"
REGISTERED_NULL_METHOD = "exact count-preserving (ADR-0013 section 14 item 8)"
PANEL_NULL_SEEDS = {"panel_a": core.NULL_SEEDS_A, "panel_b": core.NULL_SEEDS_B}
COUNT_KEYS = ("misses_all", "first_touch_all", "misses_warm", "first_touch_warm")


class SimInvariantError(ValueError):
    """A simulator invariant failed (cache above its bound after a query, trace shape)."""


class NullGenerationError(RuntimeError):
    """The registered count-preserving generator failed on a trace for which the single-set
    precondition does not hold. ADR-0016: the setting stays without a record; nothing is repaired."""


class SimulationFailed(RuntimeError):
    """``simulate_cell`` wrote a failed record (see the ``failures`` field of the sim file)."""


class SimRecordX(SimRecord):
    """``SimRecord`` plus fields added by the simulator (all descriptive of how the record arose)."""

    descriptive: bool  # outside the four primary settings (D09 sweep) -> descriptive only
    single_set: bool
    null_method: str
    counted_queries: int
    actual_misses_with_first_touch: int  # counted misses including first touches
    null_misses_with_first_touch: list[int]  # of the frequency-layout nulls (the denominator of E)
    null_layout: str  # layout the null denominator of e_ratio is simulated under: "frequency"
    null_misses_same_layout: list[
        int
    ]  # nulls simulated under the record's own layout (descriptive)
    null_miss_rate_same_layout: float
    e_same_layout: (
        float | None
    )  # actual / mean(null_misses_same_layout); descriptive, enters no class
    layout_sha256: str  # sha256 of the layout's int32 little-endian order
    null_stream_sha256: list[str]  # sha256 of each null stream's int32 little-endian rows


# --- cache rule ---------------------------------------------------------------------------------------------
def working_set(calibration: Trace) -> int:
    """W: the number of distinct slots selected on the calibration stream for this trace type
    (computed separately for answer-site and all-position traces, ADR 8.4)."""
    return int(torch.unique(calibration.selected.to(torch.int64)).numel())


def cache_pages(working: int, rows: int, rho: float) -> int:
    """C = max(1, round(rho * W / R)) (ADR 8.4). ``round`` is Python's (ties to even); for the registered
    rho in {1/16, 1/4, 1} and R in {2, 8, 32} the quotient is exact in binary floating point."""
    if rows < 1 or working < 0 or rho <= 0:
        raise ValueError("rows must be >= 1, working >= 0, rho > 0")
    return max(1, round(rho * working / rows))


# --- pages and the LRU pass ---------------------------------------------------------------------------------
def page_sequence(trace: Trace, layout: Layout, rows: int) -> Tensor:
    """``[Q, 8] int64`` page ids of every query's selected slots under ``layout`` at ``rows`` per page."""
    if int(layout.order.numel()) != trace.slots:
        raise ValueError("layout and trace disagree on the number of slots")
    pages: Tensor = layout.positions()[trace.selected.to(torch.int64)] // rows
    return pages


def page_sets(pages: Tensor) -> PageSets:
    """Per query the ascending tuple of distinct pages (P7-B's ``page_sets`` on a page-id tensor)."""
    rows = pages.to(torch.int64).sort(dim=1).values.tolist()
    return [tuple(dict.fromkeys(row)) for row in rows]


def stream_stats(sets: PageSets, warm: int) -> dict[str, Any]:
    """Distinct pages per query histogram (1..8 pages) and the counts that bound the cache results."""
    hist = [0] * (TOP + 1)
    seen: set[int] = set()
    first_half = 0
    for i, pages in enumerate(sets):
        hist[len(pages)] += 1
        seen.update(pages)
        if i + 1 == warm:
            first_half = len(seen)
    return {
        "hist": hist[1:],
        "pages_sum": sum(i * c for i, c in enumerate(hist)),
        "distinct_stream": len(seen),
        "distinct_first_half": first_half,
    }


def _lru_pass(
    order: PageSets, capacity: int, warm: int, *, context: int | None = None
) -> dict[str, Any]:
    """One LRU pass over a page-set stream in touch order. Identical to P7-B's ``lru_pass`` except that
    the stream may have any length and that the hard check allows the cache to hold the pages of the
    current query when a query needs more than ``capacity`` pages (P7-B never has C below 8)."""
    cache_: OrderedDict[int, None] = OrderedDict()
    seen: set[int] = set()
    touch = cache_.move_to_end
    evict = cache_.popitem
    add_seen = seen.add
    misses = first = 0
    at_warm = (0, 0)
    context_capacity: list[int] = []
    before = 0
    previous: tuple[int, ...] = ()
    n = len(order)
    for i in range(n):
        if i == warm:
            at_warm = (misses, first)
            before = misses - first
        if context is not None and i >= warm and (i - warm) % context == 0 and i > warm:
            context_capacity.append(misses - first - before)
            before = misses - first
        pages = order[i]
        if pages == previous:  # every page was just served: all hits, order unchanged
            continue
        previous = pages
        for page in pages:
            if page in cache_:
                touch(page)
            else:
                cache_[page] = None
                misses += 1
                if page not in seen:
                    add_seen(page)
                    first += 1
        size = len(pages)
        while len(cache_) > capacity and len(cache_) > size:
            evict(last=False)
        if len(cache_) > max(capacity, size):
            raise SimInvariantError(
                f"the cache holds {len(cache_)} pages after a query, above C = {capacity}"
            )
    if warm >= n:
        at_warm = (misses, first)
        before = misses - first
    if context is not None and n > warm:
        context_capacity.append(misses - first - before)
    return {
        "misses_all": misses,
        "first_touch_all": first,
        "misses_warm": misses - at_warm[0],
        "first_touch_warm": first - at_warm[1],
        "context_capacity": context_capacity,
    }


def lru_counts(
    sets: PageSets,
    capacity: int,
    tie: str,
    *,
    warm: int | None = None,
    stats: dict[str, Any] | None = None,
    context: int | None = None,
) -> dict[str, Any]:
    """The four counts of P7-B (``misses_all``, ``first_touch_all``, ``misses_warm``,
    ``first_touch_warm``) for the ascending page-set stream ``sets``. ``warm`` defaults to half the
    queries (P7-B's warm-up accounting). When every page the stream touches fits in the cache no eviction
    can occur, misses equal first touches exactly, and the pass is skipped (as P7-B does; checked
    against the full pass by a test); not used when ``context`` per-context counts are requested."""
    if tie not in core.TIE_RULES:
        raise ValueError(f"unknown tie rule {tie!r}")
    n = len(sets)
    warm = n // 2 if warm is None else warm
    if stats is None:
        stats = stream_stats(sets, warm)
    if context is None and stats["distinct_stream"] <= capacity:
        d_all, d_half = stats["distinct_stream"], stats["distinct_first_half"]
        return {
            "misses_all": d_all,
            "first_touch_all": d_all,
            "misses_warm": d_all - d_half,
            "first_touch_warm": d_all - d_half,
            "context_capacity": [],
        }
    order = [pages[::-1] for pages in sets] if tie == "desc" else sets
    return _lru_pass(order, capacity, warm, context=context)


def lru_misses(pages: Tensor, cache_pages_count: int, tie: str, *, warm_queries: int = 0) -> int:
    """Number of LRU misses of the page-id sequence ``pages [Q, 8]`` with ``cache_pages_count`` pages,
    counted after the first ``warm_queries`` queries (which fill the cache without being counted);
    first-touch misses are included in this count. ``tie`` in ``core.TIE_RULES`` orders the pages of one
    query (ascending or descending page id) before they are looked up, as P7-B does. Equals the
    ``misses_warm`` of ``arborlm.p7b_sim`` on the same stream at 4,096 slots."""
    sets = page_sets(pages)
    return int(lru_counts(sets, cache_pages_count, tie, warm=warm_queries)["misses_warm"])


def capacity_misses(counts: dict[str, Any]) -> int:
    """Counted capacity misses: counted misses minus counted first-touch misses (P8's ``m`` numerator)."""
    return int(counts["misses_warm"] - counts["first_touch_warm"])


# --- nulls --------------------------------------------------------------------------------------------------
def _pack_int32(stream: Tensor) -> bytes:
    values = stream.reshape(-1).to(torch.int64).tolist()
    return struct.pack(f"<{len(values)}i", *values)


@dataclass
class NullSet:
    """The count-preserving nulls of one trace: one ``Trace`` per seed, how they were made, and the
    hash of each stream (three identical hashes for the identity null)."""

    traces: list[Trace]
    method: str
    single_set: bool
    stream_sha256: list[str]
    seeds: tuple[int, ...]


def _check_null(stream: Tensor, counts: Tensor, slots: int) -> None:
    """The registered hard checks: every query holds eight distinct slots and every per-slot count
    equals the trace's."""
    ordered = stream.sort(dim=1).values
    if bool((ordered[:, 1:] == ordered[:, :-1]).any()):
        raise a_core.InvariantError("null stream: a query lacks distinct slots")
    if not bool((torch.bincount(stream.flatten(), minlength=slots) == counts).all()):
        raise a_core.InvariantError("null stream: per-slot counts differ from the trace's")


def registered_generator(
    counts: list[int], replicate_seed: int, index: int, *, queries: int
) -> Tensor:
    """The registered count-preserving stream (ADR-0013 section 14 item 8), generalised to any N.

    ``arborlm.p7a_core.frequency_matched_detail`` cannot be called at N > 32,767: its last line hashes
    the stream as 16-bit integers (``struct.error``). This is its body without that hash: the same
    checks, the same generator seed (``replicate_seed * 1000 + index``), the same call of the frozen
    ``_deal_and_repair`` and the same query permutation, so the stream equals the frozen function's
    wherever that one runs (tested)."""
    if min(counts, default=0) < 0:
        raise ValueError("a selection count is negative")
    if sum(counts) != TOP * queries:
        raise ValueError(f"counts sum to {sum(counts)} occurrences, expected {TOP} x {queries}")
    hottest = max(range(len(counts)), key=counts.__getitem__)
    if counts[hottest] > queries:
        raise ValueError(
            f"slot {hottest} is selected {counts[hottest]} times but there are only {queries} queries"
        )
    generator = random.Random(a_core.fm_generator_seed(replicate_seed, index))
    rows, _ = a_core._deal_and_repair(counts, generator, queries, TOP)
    order = list(range(queries))
    generator.shuffle(order)
    return torch.tensor([rows[i] for i in order], dtype=torch.int64)


def make_nulls(trace: Trace, null_seeds: tuple[int, ...], *, index: int = 0) -> NullSet:
    """Count-preserving nulls for ``null_seeds`` (the registered P7-A generator generalised to N slots
    and Q queries, generator seed ``seed * 1000 + index`` as in P7-B/P8). ADR-0016's identity null is used
    only when its single-set precondition holds on the trace (exactly eight slots, each selected in every
    query); otherwise the registered generator runs unchanged, and if it fails the nulls do not exist:
    ``NullGenerationError`` (no repair)."""
    from supplements.p8s.null import identity_stream, precondition_from_counts

    selected = trace.selected.to(torch.int64)
    queries = int(selected.shape[0])
    counts_t = torch.bincount(selected.flatten(), minlength=trace.slots)
    counts = counts_t.tolist()
    pre = precondition_from_counts(counts, queries)
    traces: list[Trace] = []
    hashes: list[str] = []
    if pre.holds:
        stream = identity_stream(pre.slots, queries)
        _check_null(stream, counts_t, trace.slots)
        digest = sha256(_pack_int32(stream))
        for _ in null_seeds:
            traces.append(dataclasses.replace(trace, selected=stream.clone(), branches=None))
            hashes.append(digest)
        return NullSet(traces, IDENTITY_NULL_METHOD, True, hashes, tuple(null_seeds))
    for seed in null_seeds:
        try:
            stream = registered_generator(counts, seed, index, queries=queries)
        except (ValueError, a_core.InvariantError) as error:
            raise NullGenerationError(
                f"registered generator failed (seed {seed}, index {index}): {error}"
            ) from error
        _check_null(stream, counts_t, trace.slots)
        traces.append(dataclasses.replace(trace, selected=stream, branches=None))
        hashes.append(sha256(_pack_int32(stream)))
    return NullSet(traces, REGISTERED_NULL_METHOD, False, hashes, tuple(null_seeds))


def count_preserving_null(trace: Trace, replicate_seed: int, *, index: int = 0) -> Trace:
    """A null trace with the same per-slot access counts and per-query set sizes (eight distinct slots),
    slot sharing across queries randomized (seeded) by the registered P7-A generator; for single-set
    streams the identity null (ADR 8.4 and ADR-0016) is returned. ``NullGenerationError`` if the
    registered generator fails (no repair)."""
    return make_nulls(trace, (replicate_seed,), index=index).traces[0]


# --- descriptive statistics ---------------------------------------------------------------------------------
def pages_per_query(pages: Tensor) -> float:
    """Mean number of distinct pages touched by one query (within-query co-selection, reported
    separately from cross-query reuse, ADR 8.4)."""
    ordered = pages.to(torch.int64).sort(dim=1).values
    distinct = 1 + (ordered[:, 1:] != ordered[:, :-1]).sum(dim=1)
    return float(distinct.to(torch.float64).mean())


def cross_query_reuse(pages: Tensor, window: int, *, groups: Tensor | None = None) -> float:
    """Mean over queries (that have a predecessor) of the fraction of a query's distinct pages that one
    of the previous ``window`` queries also touched. With ``groups`` (a context id per query) only
    predecessors of the same group count and queries without one are skipped. The ADR names no window
    and no grouping; the simulator default is ``CROSS_QUERY_WINDOW`` and none."""
    ordered = pages.to(torch.int64).sort(dim=1).values
    queries = int(ordered.shape[0])
    first = torch.ones_like(ordered, dtype=torch.bool)
    first[:, 1:] = ordered[:, 1:] != ordered[:, :-1]
    hit = torch.zeros_like(first)
    has_previous = torch.zeros(queries, dtype=torch.bool)
    for lag in range(1, min(window, queries - 1) + 1):
        current, previous = ordered[lag:], ordered[:-lag]
        match = (current.unsqueeze(2) == previous.unsqueeze(1)).any(dim=2)
        if groups is not None:
            same = groups[lag:] == groups[:-lag]
            match = match & same.unsqueeze(1)
            has_previous[lag:] |= same
        else:
            has_previous[lag:] = True
        hit[lag:] |= match
    distinct = first.sum(dim=1)
    hits = (hit & first).sum(dim=1)
    use = has_previous & (distinct > 0)
    if not bool(use.any()):
        return 0.0
    return float((hits[use].to(torch.float64) / distinct[use].to(torch.float64)).mean())


def e_ratio(actual: int, nulls: list[int]) -> float | None:
    """E = actual capacity misses / mean of the count-preserving nulls' capacity misses. The primary
    convention (P7-B / P8) passes the nulls simulated under the FREQUENCY layout; ``e_same_layout``
    passes those simulated under the layout itself. None when the mean is 0."""
    mean = sum(nulls) / len(nulls)
    return None if mean == 0 else actual / mean


def raw_miss_ratio(case_misses: int, reference_misses: int) -> float | None:
    """Raw miss ratio of a case to its reference (ADR 8.4 CONCENTRATION_ONLY); None for a zero reference."""
    return None if reference_misses == 0 else case_misses / reference_misses


def is_degenerate(null_miss_rate: float, single_set: bool) -> bool:
    """DEGENERATE: null miss rate below ``core.E_NULL_FLOOR`` (0.05), or a single-set stream. The null
    miss rate is that of the frequency-layout nulls, the denominator of the primary E."""
    return single_set or null_miss_rate < core.E_NULL_FLOOR


def is_descriptive(rho: float, rows: int) -> bool:
    """Settings outside the four primary ones (rho in {1/16, 1/4} x R in {8, 32}) are descriptive."""
    return not (rho in core.CACHE_RHOS_PRIMARY and rows in core.CACHE_ROWS_PRIMARY)


@cache
def _identity() -> Identity:
    return core.code_identity()


def layout_sha256(layout: Layout) -> str:
    return sha256(_pack_int32(layout.order))


# --- one setting --------------------------------------------------------------------------------------------
class _Prepared(NamedTuple):
    """Everything that depends on (trace, layout, R) but not on rho or the tie rule."""

    actual: PageSets
    actual_stats: dict[str, Any]
    nulls: list[PageSets]
    null_stats: list[dict[str, Any]]
    pages_per_query: float
    cross_query_reuse: float


def _prepare(trace: Trace, nulls: NullSet, layout: Layout, rows: int) -> _Prepared:
    pages = page_sequence(trace, layout, rows)
    warm = int(pages.shape[0]) // 2
    actual = page_sets(pages)
    null_sets = [page_sets(page_sequence(t, layout, rows)) for t in nulls.traces]
    return _Prepared(
        actual,
        stream_stats(actual, warm),
        null_sets,
        [stream_stats(s, warm) for s in null_sets],
        pages_per_query(pages),
        cross_query_reuse(pages, CROSS_QUERY_WINDOW),
    )


def _null_capacity_counts(
    prepared: _Prepared, capacity: int, tie: str, warm: int
) -> list[dict[str, Any]]:
    return [
        lru_counts(s, capacity, tie, warm=warm, stats=st)
        for s, st in zip(prepared.nulls, prepared.null_stats, strict=True)
    ]


def _record(
    prepared: _Prepared,
    reference: _Prepared,
    *,
    nulls: NullSet,
    layout: Layout,
    layout_hash: str,
    working: int,
    rows: int,
    rho: float,
    tie: str,
    label: str,
    update: int,
    stream: str,
    trace_kind: str,
    identity: Identity,
    reference_memo: dict[tuple[int, float, str], list[dict[str, Any]]] | None = None,
) -> SimRecordX:
    """``reference`` is the ``_Prepared`` of the frequency layout (same trace, nulls and R): its nulls are
    the denominator of the primary E and of the null-floor test."""
    n = len(prepared.actual)
    warm = n // 2
    counted = n - warm
    capacity = cache_pages(working, rows, rho)
    actual = lru_counts(prepared.actual, capacity, tie, warm=warm, stats=prepared.actual_stats)
    same_counts = (
        _null_capacity_counts(prepared, capacity, tie, warm) if prepared is not reference else None
    )
    memo_key = (rows, rho, tie)
    if reference_memo is not None and memo_key in reference_memo:
        null_counts = reference_memo[memo_key]
    else:
        null_counts = _null_capacity_counts(reference, capacity, tie, warm)
        if reference_memo is not None:
            reference_memo[memo_key] = null_counts
    if same_counts is None:
        same_counts = null_counts
    null_misses = [capacity_misses(c) for c in null_counts]
    same_misses = [capacity_misses(c) for c in same_counts]
    null_rate = (sum(null_misses) / len(null_misses)) / counted if counted else 0.0
    same_rate = (sum(same_misses) / len(same_misses)) / counted if counted else 0.0
    return SimRecordX(
        kind="sim",
        schema=core.SCHEMA,
        study=core.STUDY,
        label=label,
        update=update,
        stream=stream,
        trace_kind=trace_kind,
        layout=layout.key(),
        rows_per_page=rows,
        cache_fraction=rho,
        cache_pages=capacity,
        working_set=working,
        tie=tie,
        actual_misses=capacity_misses(actual),
        null_misses=null_misses,
        null_miss_rate=null_rate,
        e_ratio=e_ratio(capacity_misses(actual), null_misses),
        degenerate=is_degenerate(null_rate, nulls.single_set),
        pages_per_query=prepared.pages_per_query,
        cross_query_reuse=prepared.cross_query_reuse,
        identity=identity,
        descriptive=is_descriptive(rho, rows),
        single_set=nulls.single_set,
        null_method=nulls.method,
        counted_queries=counted,
        actual_misses_with_first_touch=int(actual["misses_warm"]),
        null_misses_with_first_touch=[int(c["misses_warm"]) for c in null_counts],
        null_layout="frequency",
        null_misses_same_layout=same_misses,
        null_miss_rate_same_layout=same_rate,
        e_same_layout=e_ratio(capacity_misses(actual), same_misses),
        layout_sha256=layout_hash,
        null_stream_sha256=list(nulls.stream_sha256),
    )


def simulate_setting(
    trace: Trace,
    calibration: Trace,
    layout: Layout,
    *,
    rows: int,
    rho: float,
    tie: str,
    null_seeds: tuple[int, ...],
    label: str,
    update: int,
    stream: str,
    index: int = 0,
    nulls: NullSet | None = None,
    identity: Identity | None = None,
) -> SimRecordX:
    """One (trace, layout, R, rho, tie) setting: W from ``calibration`` (same trace type), C from
    ``cache_pages``, actual misses, three nulls, E, null miss rate, pages per query and cross-query
    reuse. The primary E and the null-floor test use the nulls under the frequency layout fitted on
    ``calibration``; ``e_same_layout`` the nulls under ``layout``. ``index`` is the cell index of the generator seed (``seed * 1000 + index``); ``nulls`` lets a
    caller reuse the nulls of one trace across settings."""
    if calibration.kind != trace.kind or calibration.slots != trace.slots:
        raise ValueError(
            "calibration and evaluation traces must have the same trace kind and slots"
        )
    null_set = nulls if nulls is not None else make_nulls(trace, null_seeds, index=index)
    prepared = _prepare(trace, null_set, layout, rows)
    reference = (
        prepared
        if layout.name == "frequency"
        else _prepare(trace, null_set, frequency_layout(calibration), rows)
    )
    return _record(
        prepared,
        reference,
        nulls=null_set,
        layout=layout,
        layout_hash=layout_sha256(layout),
        working=working_set(calibration),
        rows=rows,
        rho=rho,
        tie=tie,
        label=label,
        update=update,
        stream=stream,
        trace_kind=trace.kind,
        identity=identity if identity is not None else _identity(),
    )


# --- one cell -----------------------------------------------------------------------------------------------
def simulate_trace_kind(
    cell: Cell,
    calibration: Trace,
    trace: Trace,
    *,
    update: int,
    stream: str,
    identity: Identity,
    layouts: dict[str, Layout] | None = None,
    layout_seed: int = RANDOM_PARTITION_SEED,
) -> tuple[list[SimRecordX], dict[str, Layout]]:
    """All settings of one trace kind of one cell: the primary settings and the D09 sweep (the primary
    four are a subset of the sweep and are not repeated), for every layout, both tie rules. Needs a
    ``frequency`` layout in ``layouts`` (``build_layouts`` always makes one): it is the null reference."""
    rows_list = core.CACHE_ROWS_SWEEP
    if layouts is None:
        clusters = (
            int(calibration.cluster.max()) + 1 if bool((calibration.cluster >= 0).any()) else 1
        )
        tree = cell.arch in ("fixed_tree", "learned_tree")
        layouts = build_layouts(
            calibration,
            rows_list,
            arch=cell.arch,
            seed=layout_seed,
            clusters=clusters,
            branches=core.BRANCHES[cell.slots] if tree else 0,
            per_branch=core.PER_BRANCH if tree else 0,
        )
    nulls = make_nulls(trace, PANEL_NULL_SEEDS[stream], index=cell.index)
    working = working_set(calibration)
    frequency = layouts["frequency"]
    references = {rows: _prepare(trace, nulls, frequency, rows) for rows in rows_list}
    memo: dict[tuple[int, float, str], list[dict[str, Any]]] = {}
    records: list[SimRecordX] = []
    for layout in layouts.values():
        digest = layout_sha256(layout)
        for rows in rows_list:
            if layout.rows is not None and layout.rows != rows:
                continue
            prepared = (
                references[rows]
                if layout.name == "frequency"
                else _prepare(trace, nulls, layout, rows)
            )
            for rho in core.CACHE_RHOS_SWEEP:
                for tie in core.TIE_RULES:
                    records.append(
                        _record(
                            prepared,
                            references[rows],
                            nulls=nulls,
                            layout=layout,
                            layout_hash=digest,
                            working=working,
                            rows=rows,
                            rho=rho,
                            tie=tie,
                            label=cell.label,
                            update=update,
                            stream=stream,
                            trace_kind=trace.kind,
                            identity=identity,
                            reference_memo=memo,
                        )
                    )
    return records, layouts


def simulate_cell(
    cell: Cell,
    run_dir: Path,
    update: int,
    stream: str,
    *,
    trace_kinds: tuple[str, ...] = ("answer", "all"),
) -> list[SimRecord]:
    """Fit the layouts on the cell's calibration trace and simulate the primary settings (rho in
    {1/16, 1/4} x R in {8, 32}, both tie rules, panel null seeds ``core.NULL_SEEDS_A/B``) and the D09
    sweep (rho in {1/16, 1/4, 1} x R in {2, 8, 32}; outside the primary four, and all rho = 1, are
    descriptive), for the actual layout and the control layouts; writes ``core.sim_path``.

    The file holds ``{"records": [...], "status", "failures", "layout_sha256"}``. If the registered
    null generator fails for a trace kind on which the single-set precondition does not hold, that kind
    gets no records, the file's status is ``failed`` with the error, and ``SimulationFailed`` is raised
    after the file is written (nothing is repaired or re-run). Layout files (int32) are written under
    ``<cell>/layouts/<update>/``."""
    if stream not in PANEL_NULL_SEEDS:
        raise ValueError("simulate_cell runs on the primary panels panel_a and panel_b only")
    if cell.arch not in ("flat", "fixed_tree", "learned_tree"):
        raise ValueError(f"a {cell.arch} cell has no memory trace")
    identity = _identity()
    records: list[SimRecord] = []
    failures: list[dict[str, str]] = []
    layout_hashes: dict[str, dict[str, str]] = {}
    for kind in trace_kinds:
        calibration = core.read_trace(
            core.trace_path(run_dir, cell.label, update, "calibration", kind)
        )
        trace = core.read_trace(core.trace_path(run_dir, cell.label, update, stream, kind))
        try:
            kind_records, layouts = simulate_trace_kind(
                cell, calibration, trace, update=update, stream=stream, identity=identity
            )
        except NullGenerationError as error:
            failures.append({"trace_kind": kind, "error": str(error)})
            continue
        records.extend(kind_records)
        directory = core.cell_dir(run_dir, cell.label) / "layouts" / core.snapshot_stem(update)
        layout_hashes[kind] = write_layouts(directory / f"layouts.{kind}.int32.bin", layouts)
    out = {
        **core.envelope("sim"),
        "label": cell.label,
        "update": update,
        "stream": stream,
        "status": "failed" if failures else "completed",
        "failures": failures,
        "layout_sha256": layout_hashes,
        "records": records,
    }
    core.write_record(core.sim_path(run_dir, cell.label, update, stream), out)
    if failures:
        raise SimulationFailed(f"{cell.label} {stream}: {failures}")
    return records


# --- which cells get which simulations (lead decision after decision 1) ---------------------------------------
FULL_SIM_BLOCKS = ("A1", "A2", "B1", "C1")  # the cells the Lane C classes, gate and references use
FULL_SIM_SLOTS = 16384
SWEEP_ONLY_BLOCKS = ("A1", "A2")
SWEEP_ONLY_SLOTS = (4096, 65536)
SCOPE_FULL = "full"
SCOPE_SWEEP_ANSWER = "sweep_answer_only"


@dataclass(frozen=True)
class SimulationScope:
    """What one registered cell is simulated for. ``full``: the primary settings and the D09 sweep on
    answer-site and all-position traces, all layouts. ``sweep_answer_only``: the D09 sweep on answer-site
    traces only (all layouts), descriptive: the cell enters no class."""

    scope: str
    trace_kinds: tuple[str, ...]
    descriptive: bool


def simulation_scope(cell: Cell) -> SimulationScope | None:
    """The scope of ``cell`` or None (the cell is not simulated). Flat and tree cells only (a dense
    cell has no memory trace). Cells of A1, A2, B1, C1 with 16,384 slots: full. Cells of A1 and A2 with
    4,096 or 65,536 slots: D09 sweep on answer-site traces, descriptive. No other cell."""
    if cell.arch not in ("flat", "fixed_tree", "learned_tree"):
        return None
    if cell.block in FULL_SIM_BLOCKS and cell.slots == FULL_SIM_SLOTS:
        return SimulationScope(SCOPE_FULL, ("answer", "all"), False)
    if cell.block in SWEEP_ONLY_BLOCKS and cell.slots in SWEEP_ONLY_SLOTS:
        return SimulationScope(SCOPE_SWEEP_ANSWER, ("answer",), True)
    return None


def simulation_plan() -> dict[str, list[Cell]]:
    """The registry's cells grouped by scope: keys ``full``, ``sweep_answer_only`` and ``not_simulated``
    (registry order within each group; every registered cell is in exactly one group)."""
    plan: dict[str, list[Cell]] = {SCOPE_FULL: [], SCOPE_SWEEP_ANSWER: [], "not_simulated": []}
    for cell in core.cells():
        scope = simulation_scope(cell)
        plan["not_simulated" if scope is None else scope.scope].append(cell)
    return plan


# --- equivalence with the frozen P7-B / P8 code (ADR 8.4: required before use) -------------------------------
P8_EVAL_RUN = "P8E-20261114T043753008527Z-ab07648862054617b63d9e4d83e5407f"
P8_SIM_RUN = "P8S-20261114T043952694180Z-088e6814edcd465894aebd125d53ddc3"
EQUIVALENCE_LABELS = (
    "b102-o302-s601-C04",  # near-collapsed, flat, 17 distinct slots
    "b102-o302-s602-C05",  # near-collapsed, tree, 16 distinct slots
    "b103-o303-s601-C01",  # ordinary flat
    "b101-o301-s601-C07",  # ordinary tree
    "b101-o301-s602-C08",
    "b103-o303-s602-C06",
)
EQUIVALENCE_SETTINGS = ((2, 32), (8, 8))  # (R, C) of ADR-0015 section 7.1


def _as_trace(label: str, stream: str, selected: Tensor, branches: Tensor | None) -> Trace:
    q = int(selected.shape[0])
    zeros = torch.zeros(q, dtype=torch.int64)
    return Trace(
        label, 0, stream, "answer", 4096, selected, branches, zeros, zeros, zeros, zeros - 1
    )


def p7b_equivalence(
    experiments_root: Path,
    *,
    eval_run: str = P8_EVAL_RUN,
    sim_run: str = P8_SIM_RUN,
    labels: tuple[str, ...] = EQUIVALENCE_LABELS,
    out: Path | None = None,
) -> dict[str, Any]:
    """Check exact equality with the frozen P7-B / P8 results on P8's recorded traces at 4,096 slots.

    For each label: this module's layouts (identity, frequency, co-access at R = 2 and 8, the
    branch-constrained co-access layout for trees, and the five P8 partition layouts built by the
    group co-access routine) are compared with the recorded ``layouts.int16.bin`` order by order and
    with the recorded canonical hash table; the sparse co-access equals P7-B's ``pair_affinity``; the nulls
    equal the recorded stream hashes; and for both panels, both settings (R = 2, C = 32; R = 8, C = 8),
    both tie rules, the actual stream under every recorded layout and each null stream under every
    recorded layout, the four counts, the per-context quantiles and the page statistics equal the
    recorded ``sim.json``. Frozen modules are imported here only, for the verification."""
    from arborlm import p7b_core as b_core
    from arborlm import p7b_layout as layout_mod
    from arborlm import p7b_sim as frozen_sim
    from arborlm import p8_core, p8_sim

    eval_root, sim_root = experiments_root / eval_run, experiments_root / sim_run
    report: dict[str, Any] = {
        "kind": "p7b_equivalence",
        "study": core.STUDY,
        "label": "self-check; not independent review, not Astra validation, not human approval",
        "eval_run": eval_run,
        "sim_run": sim_run,
        "settings": [list(s) for s in EQUIVALENCE_SETTINGS],
        "tie_rules": list(core.TIE_RULES),
        "sources": {
            "studies/p9/sim.py": file_sha256(Path(__file__)),
            "studies/p9/layout.py": file_sha256(Path(__file__).with_name("layout.py")),
        },
        "torch": torch.__version__,
        "platform": platform.platform(),
        "cells": {},
    }
    total = {
        "layouts": 0,
        "layout_hashes": 0,
        "count_groups": 0,
        "count_values": 0,
        "stats": 0,
        "ctx_q": 0,
        "null_hashes": 0,
    }
    differences: list[str] = []
    cap_for_rows = dict(EQUIVALENCE_SETTINGS)
    for label in labels:
        started = time.monotonic()
        cell = p8_core.parse_label(label)
        eval_dir = eval_root / "cells" / label
        sim_dir = sim_root / "cells" / label
        eval_record = read_json(eval_dir / "eval.json")
        sim_record = read_json(sim_dir / "sim.json")
        tree = cell.variant != "flat"
        diffs: list[str] = []
        cal_selected, cal_branches = p8_sim.load_trace(eval_dir, eval_record, "calibration")
        calibration = _as_trace(label, "calibration", cal_selected, cal_branches)
        # sparse co-access against the dense P7-B affinity
        co = sparse_coaccess(calibration)
        from .layout import adjacency

        if adjacency(co) != layout_mod.pair_affinity(cal_selected):
            diffs.append("sparse co-access differs from p7b_layout.pair_affinity")
        # layouts against the recorded file and hash table
        recorded_orders = layout_mod.read_layout_file(
            sim_dir / "layouts.int16.bin", sim_record["layouts"]["index"]
        )
        mine: dict[str, Layout] = {}
        from .layout import coaccess_layout, frequency_layout, identity_layout

        mine["L-ID"] = identity_layout(4096)
        mine["L-FREQ"] = frequency_layout(calibration)
        for rows, _ in EQUIVALENCE_SETTINGS:
            mine[f"L-COAX|R{rows}"] = coaccess_layout(calibration, rows, seed=0, co=co)
            for name, seed in zip(b_core.L_PCOAX, p8_core.PARTITION_SEEDS, strict=True):
                mine[f"{name}|R{rows}"] = group_coaccess_layout(
                    calibration, rows, layout_mod.partition_groups(seed), name=name, co=co
                )
            if tree:
                groups = layout_mod.branch_groups()
                mine[f"L-BCOAX|R{rows}"] = group_coaccess_layout(
                    calibration, rows, groups, name="L-BCOAX", co=co
                )
        hash_table = sim_record["layouts"]["hash_table"]
        for key, layout in mine.items():
            total["layouts"] += 1
            if layout.order.tolist() != recorded_orders[key]:
                diffs.append(f"layout order differs: {key}")
            rows_for_hash = (
                [int(key.partition("|R")[2])]
                if "|R" in key
                else [r for r, _ in EQUIVALENCE_SETTINGS]
            )
            for rows in rows_for_hash:
                hash_key = key if "|R" in key else b_core.layout_key(key, rows)
                total["layout_hashes"] += 1
                if b_core.canonical_hash(layout.order.tolist(), rows) != hash_table[hash_key]:
                    diffs.append(f"layout canonical hash differs: {hash_key}")
        unrecorded = sorted(set(recorded_orders) - set(mine))
        if unrecorded:
            diffs.append(f"recorded layouts not rebuilt: {unrecorded}")
        # panels
        panel_seeds = {"A": p8_core.PANEL_A_NULL_SEEDS, "B": p8_core.PANEL_B_NULL_SEEDS}
        by_panel: dict[str, Any] = {}
        for panel in ("A", "B"):
            selected, branches = p8_sim.load_trace(eval_dir, eval_record, panel)
            trace = _as_trace(label, "panel", selected, branches)
            null_set = make_nulls(trace, panel_seeds[panel], index=cell.index)
            if null_set.single_set:
                diffs.append(
                    f"panel {panel}: the single-set precondition held on a registered cell"
                )
            recorded_panel = sim_record["panels"][panel]
            for i, entry in enumerate(recorded_panel["null_streams"]):
                total["null_hashes"] += 1
                if sha256(a_core._pack(null_set.traces[i].selected, "h")) != entry["stream_sha256"]:
                    diffs.append(f"panel {panel}: null {i + 1} stream hash differs")
            streams = {
                "actual": trace,
                **{f"null_{i + 1}": t for i, t in enumerate(null_set.traces)},
            }
            compared = 0
            for stream_name, stream_trace in streams.items():
                n = int(stream_trace.selected.shape[0])
                warm = n // 2
                for key, group in recorded_panel["streams"][stream_name].items():
                    layout = mine[key] if key in mine else mine[key.partition("|R")[0]]
                    rows = int(key.partition("|R")[2])
                    sets = page_sets(page_sequence(stream_trace, layout, rows))
                    stats = stream_stats(sets, warm)
                    total["stats"] += 1
                    if stats != group["stats"]:
                        diffs.append(f"panel {panel} {stream_name} {key}: page statistics differ")
                    for tie in core.TIE_RULES:
                        ref = group["by_c"][str(cap_for_rows[rows])][tie]
                        got = lru_counts(
                            sets, cap_for_rows[rows], tie, warm=warm, context=a_core.CONTEXT
                        )
                        total["count_groups"] += 1
                        compared += 1
                        for name in COUNT_KEYS:
                            total["count_values"] += 1
                            if got[name] != ref[name]:
                                diffs.append(
                                    f"panel {panel} {stream_name} {key} {tie} {name}: {got[name]} != {ref[name]}"
                                )
                        total["ctx_q"] += 1
                        if frozen_sim.quantiles(got["context_capacity"]) != ref["ctx_q"]:
                            diffs.append(
                                f"panel {panel} {stream_name} {key} {tie}: per-context quantiles differ"
                            )
                        if (
                            lru_misses(
                                page_sequence(stream_trace, layout, rows),
                                cap_for_rows[rows],
                                tie,
                                warm_queries=warm,
                            )
                            != ref["misses_warm"]
                        ):
                            diffs.append(
                                f"panel {panel} {stream_name} {key} {tie}: lru_misses differs"
                            )
            by_panel[panel] = {"configurations_compared": compared, "queries": n}
        report["cells"][label] = {
            "variant": cell.variant,
            "cell_index_for_null_generator": cell.index,
            "unique_selected_slots_calibration": int((co.frequency > 0).sum()),
            "layouts_compared": len(mine),
            "panels": by_panel,
            "differences": diffs,
            "equal": not diffs,
            "seconds": time.monotonic() - started,
            "input_sha256": {
                "eval.json": file_sha256(eval_dir / "eval.json"),
                "sim.json": file_sha256(sim_dir / "sim.json"),
                "layouts.int16.bin": file_sha256(sim_dir / "layouts.int16.bin"),
            },
        }
        differences += [f"{label}: {d}" for d in diffs]
    report["totals"] = total
    report["differences"] = differences
    report["passed"] = not differences
    if out is not None:
        write_json(out, report)
    return report


# --- synthetic part (ADR 9) ---------------------------------------------------------------------------------
PLANTED_KINDS = (
    "popularity_only",  # E ~ 1
    "clusters_random_sharing",
    "clusters_aligned_sharing",
    "collapsed_single_set",  # identity null, DEGENERATE
    "working_set_below_cache",  # DEGENERATE
    "incomplete_input",  # INCOMPLETE
)
PLANTED_ZIPF_EXPONENT = 0.8  # skew of the planted popularity (synthetic; no ADR value)
PLANTED_BELOW_CACHE_SLOTS = 12  # distinct slots of the evaluation stream of working_set_below_cache


@dataclass
class PlantedTrace:
    """A generated trace with the class it must receive: ``expected`` in {"E~1", "LOCALITY_POSITIVE",
    "NO_DIFFERENCE", "DEGENERATE", "INCOMPLETE"}, plus the calibration trace and the cluster labels.
    For the two cluster kinds ``expected`` is relative to the random-sharing trace of the same size
    as the reference (random sharing: ``NO_DIFFERENCE``; aligned sharing: ``LOCALITY_POSITIVE``)."""

    kind: str
    trace: Trace | None
    calibration: Trace | None
    expected: str


def _distinct_rows(
    generator: torch.Generator, count: int, slots: int, weights: Tensor | None
) -> Tensor:
    """``[count, 8]`` rows of eight distinct slots drawn independently with the given weights (uniform
    when None): sample with replacement and keep each row's first eight distinct draws."""
    extra = 16
    if weights is None:
        draws = torch.randint(0, slots, (count, extra), generator=generator)
    else:
        draws = torch.multinomial(
            weights, count * extra, replacement=True, generator=generator
        ).view(count, extra)
    rows: list[list[int]] = []
    for row in draws.tolist():
        distinct = list(dict.fromkeys(row))
        while len(distinct) < TOP:  # rare: refill with single draws
            pick = (
                int(torch.randint(0, slots, (1,), generator=generator))
                if weights is None
                else int(torch.multinomial(weights, 1, generator=generator))
            )
            if pick not in distinct:
                distinct.append(pick)
        rows.append(distinct[:TOP])
    return torch.tensor(rows, dtype=torch.int64)


def _zipf_weights(slots: int, generator: torch.Generator) -> Tensor:
    rank = torch.randperm(slots, generator=generator).to(torch.float64) + 1.0
    return rank.pow(-PLANTED_ZIPF_EXPONENT).to(torch.float32)


def _epochs(generator: torch.Generator, facts: int, cluster_of: Tensor, epochs: int) -> Tensor:
    """Fact visiting order: per epoch the clusters in random order, each cluster's facts shuffled; every
    8 consecutive facts are one context (a cluster of 16 gives two contexts)."""
    clusters = int(cluster_of.max()) + 1
    members = [torch.nonzero(cluster_of == c).flatten() for c in range(clusters)]
    order: list[Tensor] = []
    for _ in range(epochs):
        for c in torch.randperm(clusters, generator=generator).tolist():
            m = members[c]
            order.append(m[torch.randperm(m.numel(), generator=generator)])
    return torch.cat(order)


def _planted_stream(
    label: str, stream: str, slots: int, selected: Tensor, fact: Tensor, cluster_of: Tensor
) -> Trace:
    q = int(selected.shape[0])
    index = torch.arange(q, dtype=torch.int64)
    return Trace(
        label=label,
        update=0,
        stream=stream,
        kind="answer",
        slots=slots,
        selected=selected,
        branches=None,
        context=index // 8,
        position=8 * (index % 8) + 6,
        fact=fact,
        cluster=cluster_of[fact],
    )


def planted_trace(kind: str, *, slots: int, seed: int) -> PlantedTrace:
    """Generate the planted-structure trace of ``kind`` with known answers (ADR 9): ``slots // 2`` facts
    in clusters of 16 (``core.CLUSTER_SIZE``), calibration = every fact twice, evaluation = every fact
    once, contexts of eight facts of one cluster, queries at answer sites (one per fact).

    * ``popularity_only``: every query draws eight distinct slots independently from one skewed
      popularity (no fact or cluster structure): E near 1 under any layout.
    * ``clusters_random_sharing``: a fact owns a fixed random set of eight slots (slots shared
      across clusters at random).
    * ``clusters_aligned_sharing``: a cluster owns a block of 32 slots (a random permutation of the
      slots cut into blocks), a fact owns eight of them: slots are shared inside a cluster only.
    * ``collapsed_single_set``: every query selects the same eight slots.
    * ``working_set_below_cache``: calibration as popularity_only over all slots (large W),
      evaluation over ``PLANTED_BELOW_CACHE_SLOTS`` slots only.
    * ``incomplete_input``: no trace at all.
    """
    if kind not in PLANTED_KINDS:
        raise ValueError(f"unknown planted kind {kind!r}")
    if kind == "incomplete_input":
        return PlantedTrace(kind, None, None, "INCOMPLETE")
    cluster_size = core.CLUSTER_SIZE
    if slots % (2 * cluster_size) or slots < 8 * cluster_size:
        raise ValueError("slots must be a multiple of 32 and at least 128")
    facts = slots // 2
    generator = torch.Generator().manual_seed(seed)
    cluster_of = torch.empty(facts, dtype=torch.int64)
    cluster_of[torch.randperm(facts, generator=generator)] = (
        torch.arange(facts, dtype=torch.int64) // cluster_size
    )
    cal_facts = _epochs(generator, facts, cluster_of, 2)
    eval_facts = _epochs(generator, facts, cluster_of, 1)
    label = f"planted-{kind}"
    expected = {
        "popularity_only": "E~1",
        "clusters_random_sharing": "NO_DIFFERENCE",
        "clusters_aligned_sharing": "LOCALITY_POSITIVE",
        "collapsed_single_set": "DEGENERATE",
        "working_set_below_cache": "DEGENERATE",
    }[kind]
    if kind == "popularity_only":
        weights = _zipf_weights(slots, generator)
        cal_sel = _distinct_rows(generator, 2 * facts, slots, weights)
        eval_sel = _distinct_rows(generator, facts, slots, weights)
    elif kind == "collapsed_single_set":
        one = torch.randperm(slots, generator=generator)[:TOP].sort().values
        cal_sel, eval_sel = one.repeat(2 * facts, 1), one.repeat(facts, 1)
    elif kind == "working_set_below_cache":
        weights = _zipf_weights(slots, generator)
        cal_sel = _distinct_rows(generator, 2 * facts, slots, weights)
        few = torch.randperm(slots, generator=generator)[:PLANTED_BELOW_CACHE_SLOTS]
        pick = torch.rand(facts, PLANTED_BELOW_CACHE_SLOTS, generator=generator).argsort(dim=1)[
            :, :TOP
        ]
        eval_sel = few[pick]
    else:
        if kind == "clusters_random_sharing":
            fact_slots = _distinct_rows(generator, facts, slots, None)
        else:
            block = 2 * cluster_size  # 32 slots per cluster
            blocks = torch.randperm(slots, generator=generator).view(-1, block)
            choice = torch.rand(facts, block, generator=generator).argsort(dim=1)[:, :TOP]
            fact_slots = torch.gather(blocks[cluster_of], 1, choice)
        cal_sel, eval_sel = fact_slots[cal_facts], fact_slots[eval_facts]
    calibration = _planted_stream(label, "calibration", slots, cal_sel, cal_facts, cluster_of)
    trace = _planted_stream(label, "panel_a", slots, eval_sel, eval_facts, cluster_of)
    return PlantedTrace(kind, trace, calibration, expected)


def key_traffic(arch: str, slots: int, key_width: int, queries: int) -> dict[str, int | str]:
    """Key traffic with keys in RAM (zero) against keys on storage (flat reads every key row; the tree
    reads the router and two branches): an arithmetic identity from ``core.logical_key_products``,
    labelled ``"identity"``, not a simulation result (ADR 9). Bytes assume FP32 keys of ``key_width``
    (and a router row of the same width); logical key rows read per query are
    ``core.logical_key_products``."""
    rows = core.logical_key_products(arch, slots)
    per_query = rows * key_width * 4
    return {
        "basis": "identity",
        "note": "arithmetic identity from ADR 5.2, not a simulation result and not storage I/O",
        "arch": arch,
        "slots": slots,
        "key_width": key_width,
        "queries": queries,
        "keys_in_ram_bytes_per_query": 0,
        "keys_in_ram_total_bytes": 0,
        "key_rows_per_query": rows,
        "keys_on_storage_bytes_per_query": per_query,
        "keys_on_storage_total_bytes": per_query * queries,
    }


# --- CLI ------------------------------------------------------------------------------------------------------
def _planted_summary(kind: str, slots: int, seed: int) -> dict[str, Any]:
    """E of one planted trace at R = 8 and the two primary cache fractions, for four layouts."""
    planted = planted_trace(kind, slots=slots, seed=seed)
    if planted.trace is None or planted.calibration is None:
        return {"kind": kind, "expected": planted.expected}
    clusters = int(planted.calibration.cluster.max()) + 1
    layouts = build_layouts(
        planted.calibration, (8,), arch="flat", seed=RANDOM_PARTITION_SEED, clusters=clusters
    )
    nulls = make_nulls(planted.trace, core.NULL_SEEDS_A, index=0)
    keep = (
        "layout",
        "cache_fraction",
        "e_ratio",
        "e_same_layout",
        "degenerate",
        "null_miss_rate",
        "null_miss_rate_same_layout",
        "pages_per_query",
    )
    rows: list[dict[str, Any]] = []
    for key in ("identity", "frequency", "coaccess@8", "oracle_cluster"):
        for rho in core.CACHE_RHOS_PRIMARY:
            record = simulate_setting(
                planted.trace,
                planted.calibration,
                layouts[key],
                rows=8,
                rho=rho,
                tie="asc",
                null_seeds=core.NULL_SEEDS_A,
                label=planted.trace.label,
                update=0,
                stream="panel_a",
                nulls=nulls,
            )
            rows.append({k: dict(record)[k] for k in keep})
    return {"kind": kind, "expected": planted.expected, "settings": rows}


def main(argv: list[str] | None = None) -> int:
    """CLI ``uv run --locked python -m studies.p9.sim {cell,equivalence,planted} ...``. (``stage`` is the
    job manager's, ``pool.py``, package I6: not implemented here.)"""
    parser = argparse.ArgumentParser(prog="python -m studies.p9.sim")
    sub = parser.add_subparsers(dest="command", required=True)
    c = sub.add_parser("cell", help="simulate one cell's snapshot on one panel")
    c.add_argument("--run-dir", type=Path, required=True)
    c.add_argument("--label", required=True)
    c.add_argument("--update", type=int, required=True)
    c.add_argument("--stream", choices=sorted(PANEL_NULL_SEEDS), required=True)
    c.add_argument("--trace-kinds", nargs="*", default=["answer", "all"])
    e = sub.add_parser(
        "equivalence", help="exact equivalence with the frozen P7-B/P8 results at 4,096 slots"
    )
    e.add_argument("--experiments-root", type=Path, default=None)
    e.add_argument("--eval-run", default=P8_EVAL_RUN)
    e.add_argument("--sim-run", default=P8_SIM_RUN)
    e.add_argument("--labels", nargs="*", default=list(EQUIVALENCE_LABELS))
    e.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("planted", help="planted-trace summary of one kind")
    p.add_argument("--kind", choices=PLANTED_KINDS, required=True)
    p.add_argument("--slots", type=int, default=4096)
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    if args.command == "equivalence":
        root = args.experiments_root or core.default_experiments_root()
        report = p7b_equivalence(
            root,
            eval_run=args.eval_run,
            sim_run=args.sim_run,
            labels=tuple(args.labels),
            out=args.out,
        )
        print(
            json.dumps(
                {
                    "passed": report["passed"],
                    "totals": report["totals"],
                    "differences": report["differences"][:20],
                    "out": str(args.out),
                },
                indent=1,
            )
        )
        return 0 if report["passed"] else 1
    if args.command == "planted":
        core.assert_not_registered_seed(args.seed)
        summary = _planted_summary(args.kind, args.slots, args.seed)
        if args.out is not None:
            write_json(args.out, summary)
        print(json.dumps(summary, indent=1))
        return 0
    cell = core.parse_label(args.label)
    simulate_cell(cell, args.run_dir, args.update, args.stream, trace_kinds=tuple(args.trace_kinds))
    return 0


if __name__ == "__main__":
    sys.exit(main())
