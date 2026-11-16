"""P7-B page simulator: value pages only (ADR-0014 section 5). Pure integer bookkeeping.

No model is imported or run, and no key-read code path exists in this module (the P7-A defect
affected only simulated key reads, which P7-B leaves out entirely). The cache model is ADR-0013's:
one cache of value pages with capacity C; a query is served as a unit (its distinct pages are looked
up, misses are fetched, then the least recently used pages *not used by the current query* are
evicted down to C); warm-up on the first half of the stream, counting on the second half; a miss is
first-touch when the page was never read before in the stream, otherwise a capacity miss.

Pages of one query are touched in ascending page number (tie rule ``asc``: the lowest page of the
oldest query is evicted first) or in descending page number (tie rule ``desc``). Both rules are run
for every criterion (section 5). Hard check: after every query the cache holds at most C pages.

Page sets are computed once per (stream, layout, R) and reused across capacities and tie rules.

Status: implementation self-checked only. Not independent review, not Astra validation.
"""

import math
import time
from collections import OrderedDict
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Any

import torch
from torch import Tensor

from . import p7b_core as core

PageSets = list[tuple[int, ...]]
QUANTILES = (0.0, 0.05, 0.25, 0.5, 0.75, 0.95, 1.0)  # implementer choice (section 6 names none)
COUNT_KEYS = ("misses_all", "first_touch_all", "misses_warm", "first_touch_warm")


class CapExceeded(TimeoutError):
    """The worker's own simulation deadline passed; the partial record is preserved."""


class EvaluationTrace:
    """An evaluation-stream trace handed to the simulator. Deliberately a different type from
    ``p7b_layout.CalibrationTrace``: layout builders refuse it."""

    __slots__ = ("branches", "kind", "label", "selected", "stream")

    def __init__(
        self, selected: Tensor, branches: Tensor | None, kind: str, label: str, stream: str
    ) -> None:
        self.selected = selected.to(torch.int64)
        self.branches = None if branches is None else branches.to(torch.int64)
        self.kind, self.label, self.stream = kind, label, stream


# --- page sets
def positions_tensor(order: list[int]) -> Tensor:
    positions = torch.empty(core.SLOTS, dtype=torch.int64)
    positions[torch.tensor(order, dtype=torch.int64)] = torch.arange(core.SLOTS, dtype=torch.int64)
    return positions


def page_sets(positions: Tensor, rows_per_page: int, selected: Tensor) -> PageSets:
    """Per query the ascending tuple of distinct pages holding its selected rows."""
    pages = (positions[selected.to(torch.int64)] // rows_per_page).sort(dim=1).values.tolist()
    return [tuple(dict.fromkeys(row)) for row in pages]


# --- C-independent statistics
def stream_stats(queries: PageSets, max_pages: int = core.TOP) -> dict[str, Any]:
    """Distribution of distinct pages per query and the counts that bound the cache results."""
    hist = [0] * (max_pages + 1)
    seen: set[int] = set()
    first_half = 0
    warm = len(queries) // 2
    for i, pages in enumerate(queries):
        hist[len(pages)] += 1
        seen.update(pages)
        if i + 1 == warm:
            first_half = len(seen)
    return {
        "hist": hist[1:],  # queries with 1..8 distinct pages
        "pages_sum": sum(i * c for i, c in enumerate(hist)),
        "distinct_stream": len(seen),
        "distinct_first_half": first_half,
    }


def quantiles(values: list[int]) -> list[int]:
    ordered = sorted(values)
    n = len(ordered)
    return [ordered[int(q * (n - 1))] for q in QUANTILES]


# --- LRU
def lru_pass(
    queries: PageSets,
    capacity: int,
    *,
    touch_order: PageSets | None = None,
    evict_extra: int = 0,
) -> dict[str, Any]:
    """One direct LRU pass over a page-set stream.

    ``queries`` are the ascending page tuples. ``touch_order`` (default ``queries``) is what is
    touched, one query at a time: pass the reversed tuples for the descending tie rule. Returns the
    four counts of ADR-0013 (all queries; counted half) and the per-context capacity-miss quantiles
    over the counted contexts. Raises ``InvariantError`` if the cache holds more than ``capacity``
    pages after a query. ``evict_extra`` is a testing hook: it lets the cache keep that many extra
    pages so the hard check must fire.
    """
    n = len(queries)
    warm = n // 2
    if n % core.CONTEXT or (n // core.CONTEXT) % 2:
        raise ValueError("a stream must hold an even number of whole 64-query contexts")
    order = touch_order if touch_order is not None else queries
    cache: OrderedDict[int, None] = OrderedDict()
    seen: set[int] = set()
    touch = cache.move_to_end
    evict = cache.popitem
    add_seen = seen.add
    limit = capacity + evict_extra
    misses = first = 0
    totals: list[int] = []
    context_capacity: list[int] = []
    previous: tuple[int, ...] = ()
    for lo, hi in ((0, warm), (warm, n)):
        counted = lo == warm
        for start in range(lo, hi, core.CONTEXT):
            before = misses - first
            for i in range(start, start + core.CONTEXT):
                pages = order[i]
                if pages == previous:  # every page was just served: all hits, order unchanged
                    continue
                previous = pages
                for page in pages:
                    if page in cache:
                        touch(page)
                    else:
                        cache[page] = None
                        misses += 1
                        if page not in seen:
                            add_seen(page)
                            first += 1
                size = len(pages)
                while len(cache) > limit and len(cache) > size:
                    evict(last=False)
                if len(cache) > capacity:
                    raise core.InvariantError(
                        f"the cache holds {len(cache)} pages after a query, above C = {capacity}"
                    )
            if counted:
                context_capacity.append(misses - first - before)
        totals += [misses, first]
    return {
        "misses_all": totals[2],
        "first_touch_all": totals[3],
        "misses_warm": totals[2] - totals[0],
        "first_touch_warm": totals[3] - totals[1],
        "ctx_q": quantiles(context_capacity),
    }


def reversed_order(queries: PageSets) -> PageSets:
    return [pages[::-1] for pages in queries]


def cache_counts(
    queries: PageSets,
    capacity: int,
    stats: dict[str, Any],
    *,
    descending: bool = False,
    touch_order: PageSets | None = None,
) -> dict[str, Any]:
    """Counts at one capacity. When every page the stream ever touches fits in the cache no
    eviction can occur and misses equal first touches exactly, so the pass is skipped (checked
    against the full pass by a test)."""
    if stats["distinct_stream"] <= capacity:
        d_all, d_half = stats["distinct_stream"], stats["distinct_first_half"]
        return {
            "misses_all": d_all,
            "first_touch_all": d_all,
            "misses_warm": d_all - d_half,
            "first_touch_warm": d_all - d_half,
            "ctx_q": [0] * len(QUANTILES),
        }
    order = (
        touch_order
        if touch_order is not None
        else (reversed_order(queries) if descending else queries)
    )
    return lru_pass(queries, capacity, touch_order=order)


def check_group(
    stats: dict[str, Any], by_c: dict[int, dict[str, dict[str, Any]]], where: str
) -> None:
    """Section 10 invariants for one (stream, layout, R) group across capacities and tie rules:
    misses never exceed page touches; first-touch misses depend on neither C nor the tie rule;
    capacity misses do not increase with C (each tie rule), for the counted half and for the whole
    stream, as in P7-A."""
    touches = stats["pages_sum"]
    expected_first = (
        stats["distinct_stream"],
        stats["distinct_stream"] - stats["distinct_first_half"],
    )
    for tie in core.TIES:
        previous: int | None = None
        previous_all: int | None = None
        for capacity in sorted(by_c):
            row = by_c[capacity].get(tie)
            if row is None:
                continue
            if row["misses_all"] > touches or row["misses_warm"] > touches:
                raise core.InvariantError(f"{where} C={capacity} {tie}: misses exceed page touches")
            if (row["first_touch_all"], row["first_touch_warm"]) != expected_first:
                raise core.InvariantError(
                    f"{where} C={capacity} {tie}: first-touch misses depend on C or the tie rule"
                )
            if (
                row["misses_all"] < row["first_touch_all"]
                or row["misses_warm"] < row["first_touch_warm"]
            ):
                raise core.InvariantError(
                    f"{where} C={capacity} {tie}: fewer misses than first touches"
                )
            if row["misses_all"] < stats["distinct_stream"]:
                raise core.InvariantError(
                    f"{where} C={capacity} {tie}: cold misses below distinct pages"
                )
            capacity_misses = row["misses_warm"] - row["first_touch_warm"]
            capacity_misses_all = row["misses_all"] - row["first_touch_all"]  # whole stream (P7-A)
            if (previous is not None and capacity_misses > previous) or (
                previous_all is not None and capacity_misses_all > previous_all
            ):
                raise core.InvariantError(
                    f"{where} C={capacity} {tie}: capacity misses grew with C"
                )
            previous, previous_all = capacity_misses, capacity_misses_all


def check_r1_invariants(record: dict[str, Any]) -> dict[str, Any]:
    """ADR-0014 section 4 (R = 1) as a run-time check: every page holds one row, so layouts cannot
    change which rows share a page. In every stream, across every layout simulated at R = 1, the
    distinct-pages-per-query statistics, both first-touch counts and the capacity misses at C = 8
    must be identical (at larger C the tie rule makes page numbering matter, which is not a
    violation). Raises ``InvariantError`` otherwise."""
    key_r1 = "|R1"
    checked = 0
    for stream, groups in record["streams"].items():
        first: tuple[str, Any] | None = None
        for key, group in groups.items():
            if not key.endswith(key_r1):
                continue
            row = group["by_c"].get("8", {}).get("asc")
            if row is None:
                continue
            signature = (
                group["stats"],
                row["first_touch_all"],
                row["first_touch_warm"],
                row["misses_all"] - row["first_touch_all"],
                row["misses_warm"] - row["first_touch_warm"],
            )
            if first is None:
                first = (key, signature)
            elif signature != first[1]:
                raise core.InvariantError(
                    f"R = 1 invariant violated in stream {stream}: {key} differs from {first[0]} "
                    "in distinct pages per query, first-touch misses or capacity misses at C = 8"
                )
            checked += 1
    return {"r1_groups_compared": checked, "all_identical": True}


def simulate_group(
    queries: PageSets,
    asc: tuple[int, ...],
    desc: tuple[int, ...],
    where: str,
) -> dict[str, Any]:
    """Statistics and counts of one (stream, layout, R) group: ascending rule at ``asc``
    capacities, descending rule at ``desc`` capacities. The page sets are built once."""
    stats = stream_stats(queries)
    by_c: dict[int, dict[str, dict[str, Any]]] = {}
    for capacity in sorted(set(asc) | set(desc)):
        by_c.setdefault(capacity, {})
    for capacity in asc:
        by_c[capacity]["asc"] = cache_counts(queries, capacity, stats)
    if desc:
        reverse = reversed_order(queries)
        for capacity in desc:
            by_c[capacity]["desc"] = cache_counts(
                queries, capacity, stats, descending=True, touch_order=reverse
            )
    check_group(stats, by_c, where)
    return {"stats": stats, "by_c": {str(c): v for c, v in by_c.items()}}


# --- the configuration set (sections 6 and 11)
def null_layouts(kind: str) -> tuple[str, ...]:
    """Layouts on which the order-shuffled stream and the three nulls run at every R and C:
    L-FREQ, L-COAX and (trees) L-BCOAX (section 6), plus L-ID, which ADR-0014 section 10 requires
    for the reproduction of P7-A's null and order-shuffled records on stream A."""
    base = (core.L_ID, core.L_FREQ, core.L_COAX)
    return (*base, core.L_BCOAX) if core.is_tree(kind) else base


def desc_actual_layouts(kind: str) -> tuple[str, ...]:
    """Layouts simulated on the actual stream under the descending rule at the two criterion
    settings: every layout that enters a criterion or the L-NCOAX control band."""
    base = (core.L_FREQ, core.L_COAX, core.L_NCOAX, *core.L_PCOAX)
    return (*base, core.L_BCOAX) if core.is_tree(kind) else base


def desc_null_layouts(kind: str) -> tuple[str, ...]:
    """Layouts on which the three nulls run under the descending rule at the criterion settings."""
    base = (core.L_FREQ, core.L_COAX, *core.L_PCOAX)
    return (*base, core.L_BCOAX) if core.is_tree(kind) else base


def layout_order(kind: str) -> tuple[str, ...]:
    """Processing order: the layouts P7-A also ran first, so the reproduction check can stop the
    worker early."""
    first = core.r_independent_layouts(kind)
    return (*first, *core.coaccess_layouts(kind))


def reproduced_layouts(kind: str) -> dict[str, tuple[str, ...]]:
    """Section 10: P7-A ran the actual stream on L-ID, L-RAND, L-FREQ, L-BFREQ, and the null and
    order-shuffled streams on L-ID and L-FREQ (ascending rule)."""
    actual = core.r_independent_layouts(kind)
    return {
        core.STREAM_ACTUAL: actual,
        core.STREAM_ORDER: (core.L_ID, core.L_FREQ),
        **{s: (core.L_ID, core.L_FREQ) for s in core.STREAMS_NULL},
    }


@dataclass(frozen=True)
class Group:
    layout: str
    stream: str
    rows: int
    asc: tuple[int, ...]
    desc: tuple[int, ...]


def plan(kind: str) -> list[Group]:
    """The complete simulation plan of one checkpoint on one evaluation stream.

    * actual stream: every layout at every R and C (ascending rule);
    * order-shuffled stream and the three nulls: ``null_layouts`` at every R and C (ascending);
    * the three nulls on each of the five partition layouts at the two criterion settings,
      ascending and descending;
    * descending rule at the two criterion settings: the actual stream on ``desc_actual_layouts``
      and the nulls on ``desc_null_layouts``.
    """
    asc: dict[tuple[str, str, int], set[int]] = {}
    desc: dict[tuple[str, str, int], set[int]] = {}

    def add(layout: str, stream: str, rows: int, cap: int, tie: str) -> None:
        (asc if tie == "asc" else desc).setdefault((layout, stream, rows), set()).add(cap)

    for layout in core.all_layouts(kind):
        for rows in core.RS:
            for cap in core.CS:
                add(layout, core.STREAM_ACTUAL, rows, cap, "asc")
    for layout in null_layouts(kind):
        for stream in (core.STREAM_ORDER, *core.STREAMS_NULL):
            for rows in core.RS:
                for cap in core.CS:
                    add(layout, stream, rows, cap, "asc")
    for layout in core.L_PCOAX:
        for stream in core.STREAMS_NULL:
            for rows, cap in core.CRITERION_SETTINGS:
                add(layout, stream, rows, cap, "asc")
    for rows, cap in core.CRITERION_SETTINGS:
        for layout in desc_actual_layouts(kind):
            add(layout, core.STREAM_ACTUAL, rows, cap, "desc")
            asc.setdefault((layout, core.STREAM_ACTUAL, rows), set()).add(cap)
        for layout in desc_null_layouts(kind):
            for stream in core.STREAMS_NULL:
                add(layout, stream, rows, cap, "desc")
                asc.setdefault((layout, stream, rows), set()).add(cap)
    keys = sorted(
        set(asc) | set(desc),
        key=lambda k: (layout_order(kind).index(k[0]), core.STREAMS_ALL.index(k[1]), k[2]),
    )
    return [
        Group(
            layout,
            stream,
            rows,
            tuple(sorted(asc.get((layout, stream, rows), ()))),
            tuple(sorted(desc.get((layout, stream, rows), ()))),
        )
        for layout, stream, rows in keys
    ]


def plan_size(kind: str) -> dict[str, int]:
    groups = plan(kind)
    return {
        "groups": len(groups),
        "ascending_runs": sum(len(g.asc) for g in groups),
        "descending_runs": sum(len(g.desc) for g in groups),
    }


# --- a checkpoint
class LayoutSet:
    """Position tensors of the layouts of one checkpoint, by (name, R)."""

    def __init__(self, orders: dict[str, list[int]]) -> None:
        self.orders = orders
        self._cache: dict[str, Tensor] = {}

    def positions(self, name: str, rows: int) -> Tensor:
        key = core.layout_key(name, rows) if core.is_r_specific(name) else name
        tensor = self._cache.get(key)
        if tensor is None:
            tensor = positions_tensor(self.orders[key])
            self._cache[key] = tensor
        return tensor


def effective_record(counts: list[int]) -> dict[str, Any]:
    h = core.entropy_nats(counts)
    return {
        "unique_selected_slots": sum(1 for c in counts if c),
        "entropy_nats": h,
        "effective_slots": math.exp(h),
        "counts_sha256": core.counts_sha256(counts),
    }


def simulate_checkpoint(
    *,
    trace: EvaluationTrace,
    layouts: LayoutSet,
    null_selected: dict[str, Tensor],
    deadline: float | None = None,
    progress: Callable[[dict[str, Any]], None] | None = None,
    checkpoint: Callable[[dict[str, Any]], None] | None = None,
    groups: list[Group] | None = None,
) -> dict[str, Any]:
    """Run the complete plan on one evaluation trace. ``progress(info)`` is called after every
    finished layout and at the end with the record so far (``info["record"]``), so a worker can
    keep a partial record on disk. ``null_selected`` maps ``null_1..3`` to the
    count-preserving streams. ``checkpoint(record)`` is called once the layouts that P7-A also ran
    are finished (the reproduction stop point). Raises ``CapExceeded`` with ``.partial`` if
    ``deadline`` (``time.monotonic``) passes."""
    started = time.monotonic()
    kind = trace.kind
    counts = torch.bincount(trace.selected.flatten(), minlength=core.SLOTS).tolist()
    record: dict[str, Any] = {
        "kind": kind,
        "label": trace.label,
        "stream": trace.stream,
        "queries": int(trace.selected.shape[0]),
        "evaluation_counts": effective_record(counts),
        "streams": {s: {} for s in core.STREAMS_ALL},
        "complete": False,
    }
    items = groups if groups is not None else plan(kind)
    queries_n = int(trace.selected.shape[0])
    from . import p7a_core as a_core

    reorder = a_core.query_order(a_core.STREAM_ORDER, queries_n)
    base_sets: dict[tuple[str, int], PageSets] = {}
    first_batch = {name for name in core.r_independent_layouts(kind)}
    first_done = False
    current_layout = None
    for item in items:
        if deadline is not None and time.monotonic() > deadline:
            error = CapExceeded("simulation deadline passed; partial record preserved")
            error.partial = record  # type: ignore[attr-defined]
            raise error
        if current_layout is not None and item.layout != current_layout:
            base_sets = {k: v for k, v in base_sets.items() if k[0] == item.layout}
            if progress is not None:  # a partial record after every finished layout (watchdog kill)
                progress(
                    {
                        "finished_layout": current_layout,
                        "groups": len(items),
                        "elapsed": time.monotonic() - started,
                        "complete": False,
                        "record": record,
                    }
                )
        if not first_done and item.layout not in first_batch:
            first_done = True
            if checkpoint is not None:
                checkpoint(record)
        current_layout = item.layout
        positions = layouts.positions(item.layout, item.rows)
        if item.stream == core.STREAM_ACTUAL:
            queries = base_sets.get((item.layout, item.rows))
            if queries is None:
                queries = page_sets(positions, item.rows, trace.selected)
                base_sets[(item.layout, item.rows)] = queries
        elif item.stream == core.STREAM_ORDER:
            base = base_sets.get((item.layout, item.rows))
            if base is None:
                base = page_sets(positions, item.rows, trace.selected)
                base_sets[(item.layout, item.rows)] = base
            queries = [base[i] for i in reorder]
        else:
            queries = page_sets(positions, item.rows, null_selected[item.stream])
        key = core.layout_key(item.layout, item.rows)
        where = f"{item.stream}|{key}"
        record["streams"][item.stream][key] = simulate_group(queries, item.asc, item.desc, where)
    if not first_done and checkpoint is not None:
        checkpoint(record)
    record["complete"] = True
    record["seconds"] = time.monotonic() - started
    if progress is not None:
        progress(
            {
                "finished_layout": current_layout,
                "groups": len(items),
                "elapsed": record["seconds"],
                "complete": True,
                "record": record,
            }
        )
    return record


def iter_counts(record: dict[str, Any]) -> Iterator[tuple[str, str, str, str, dict[str, Any]]]:
    """(stream, layout key, C, tie, counts) for every simulated entry."""
    for stream, groups in record["streams"].items():
        for key, group in groups.items():
            for cap, ties in group["by_c"].items():
                for tie, counts in ties.items():
                    yield stream, key, cap, tie, counts


# --- reproduction of P7-A on stream A (section 10)
def check_reproduction(record: dict[str, Any], reference: dict[str, Any]) -> dict[str, Any]:
    """Every miss count of the configurations P7-A ran (ascending rule, every R and C) must equal
    P7-A's record, as must the page statistics. A difference raises ``StopError``."""
    kind = record["kind"]
    compared = 0
    for stream, layouts in reproduced_layouts(kind).items():
        p7a_stream = core.A_NULL_NAMES.get(stream, stream)
        for layout in layouts:
            for rows in core.RS:
                key = core.layout_key(layout, rows)
                ours = record["streams"][stream][key]
                theirs = reference["streams"][p7a_stream][key]
                for field in ("hist", "pages_sum", "distinct_stream", "distinct_first_half"):
                    if ours["stats"][field] != theirs["stats"][field]:
                        raise core.StopError(
                            f"P7-A reproduction failed: {stream} {key} stats.{field} differs"
                        )
                for cap in core.CS:
                    mine = ours["by_c"][str(cap)]["asc"]
                    ref = theirs["by_c"][str(cap)]
                    for name in COUNT_KEYS:
                        if mine[name] != ref[name]:
                            raise core.StopError(
                                f"P7-A reproduction failed: {stream} {key} C={cap} {name}: "
                                f"{mine[name]} != {ref[name]}"
                            )
                    compared += 1
    return {"configurations_compared": compared, "all_equal": True}
