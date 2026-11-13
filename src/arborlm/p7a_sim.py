"""P7-A page simulator (ADR-0013 section 5 and clarifications 2-5). Pure integer bookkeeping.

No model is imported or run. The input is a trace (selected slot IDs per query, visited branches for
trees) plus layouts; the output is a compact JSON-able record. Queries are consumed in exactly the
registered stream order, one query at a time, regardless of how a model batched them.

Cache model (section 5): one cache of value pages with capacity C pages. A query is served as a
unit: its distinct pages are determined first; pages not in the cache are misses; all of the
query's pages are then held, evicting the least recently used pages not used by the current query.
Recency is per query. Pages that share a recency (last used by the same query) are evicted in
ascending page number: pages of a query are touched in ascending order, so the lowest page of the
oldest query is the first eviction (ADR-0013 section 14 item 10, the registered rule). The
descending order exists only as ``lru_pass(..., descending=True)`` for the primary-setting
sensitivity result, which carries no criterion. When a query needs more pages than C (only
possible for the key cache of section 5, never for value pages because C >= 8) the cache may
temporarily hold the whole query.

Status: implementation self-checked only.
"""

import time
from collections import Counter, OrderedDict
from collections.abc import Callable
from typing import Any

import torch
from torch import Tensor

from . import p7a_core as core
from .p7a_core import (
    BOOTSTRAP_RESAMPLES,
    BOOTSTRAP_SEED,
    BRANCHES,
    CONTEXT,
    CONTEXTS,
    CS,
    CUMULATIVE_POINTS,
    FM_SEEDS,
    KEY_LAYOUTS,
    KEY_ROW_BYTES,
    LAYOUT_FREQ,
    LAYOUT_ID,
    LAYOUTS_OTHER,
    PAGE_BYTES_FOR_R,
    PER_BRANCH,
    QUERIES,
    RS,
    SLOTS,
    STREAM_ACTUAL,
    STREAM_CONTEXT,
    STREAM_ORDER,
    STREAMS_FM,
    TOP,
    InvariantError,
)

PageSets = list[tuple[int, ...]]


class CapExceeded(TimeoutError):
    """The worker's own simulation deadline passed; the partial record is preserved."""


# --- page sets ------------------------------------------------------------------------------------
def page_sets(positions: list[int], rows_per_page: int, selected: Tensor) -> PageSets:
    """Per query the ascending tuple of distinct pages holding its selected rows."""
    pos = torch.tensor(positions, dtype=torch.int64)
    pages = (pos[selected.to(torch.int64)] // rows_per_page).sort(dim=1).values.tolist()
    return [tuple(dict.fromkeys(row)) for row in pages]


def key_page_sets(positions: list[int], key_rows_per_page: int, branches: Tensor) -> PageSets:
    """Per query the ascending distinct pages holding the 512 key rows of its two visited branches.
    One tuple per unordered branch pair is computed and reused."""
    cache: dict[tuple[int, int], tuple[int, ...]] = {}
    out: PageSets = []
    for a, b in branches.to(torch.int64).tolist():
        key = core.pair_key(a, b)
        pages = cache.get(key)
        if pages is None:
            rows = [
                positions[slot]
                for branch in key
                for slot in range(branch * PER_BRANCH, (branch + 1) * PER_BRANCH)
            ]
            pages = tuple(sorted({row // key_rows_per_page for row in rows}))
            cache[key] = pages
        out.append(pages)
    return out


# --- C-independent statistics of one page-set stream ----------------------------------------------
def stream_stats(
    queries: PageSets, max_pages: int = TOP
) -> tuple[dict[str, Any], list[int], list[int]]:
    """Distinct-page distribution, per-context pages, cumulative curve and page reuse.

    Returns the compact statistics plus, per context, the sum of per-query distinct pages and the
    number of distinct pages in the context (used by the bootstrap and kept out of the record).
    Reuse is the pooled fraction (reused page touches / page touches) over queries that have an
    immediately preceding query; pairs inside a context (position > 0) and pairs that cross a
    context boundary (position 0, not the first query) are pooled separately.
    """
    n = len(queries)
    warm = n // 2
    points = [p for p in CUMULATIVE_POINTS if p <= n]
    hist = [0] * (max_pages + 1)
    seen: set[int] = set()
    curve: list[int] = []
    first_half = 0
    reuse_in = [0, 0]
    reuse_cross = [0, 0]
    prev: set[int] = set()
    context_sum: list[int] = []
    context_distinct: list[int] = []
    running = 0
    for i, pages in enumerate(queries):
        hist[len(pages)] += 1
        running += len(pages)
        current = set(pages)
        if i:
            bucket = reuse_in if i % CONTEXT else reuse_cross
            bucket[0] += len(current & prev)
            bucket[1] += len(pages)
        prev = current
        seen |= current
        if i + 1 == warm:
            first_half = len(seen)
        if (i + 1) in points:
            curve.append(len(seen))
        if (i + 1) % CONTEXT == 0:
            context_sum.append(running)
            running = 0
    for start in range(0, n, CONTEXT):
        context_distinct.append(len(set().union(*queries[start : start + CONTEXT])))
    stats = {
        "hist": hist[1:],  # queries with 1..8 distinct pages
        "pages_sum": sum(i * c for i, c in enumerate(hist)),
        "distinct_stream": len(seen),
        "distinct_first_half": first_half,
        "distinct_per_context_sum": sum(context_distinct),
        "curve_points": points,
        "curve": curve,
        "reuse_within": reuse_in,
        "reuse_cross": reuse_cross,
    }
    return stats, context_sum, context_distinct


# --- LRU ------------------------------------------------------------------------------------------
def lru_pass(
    queries: PageSets,
    capacity: int,
    warm_start: int | None = None,
    *,
    descending: bool = False,
) -> list[int]:
    """Direct LRU, one pass. Returns [misses_all, first_touch_all, misses_warm, first_touch_warm]
    where ``warm`` counts queries from ``warm_start`` on. A miss is first-touch when the page has
    not been read before in the stream (the warm-up included), otherwise a capacity miss.

    ``descending`` touches each query's pages from the highest to the lowest, so ties among the
    pages of one query are evicted in descending page number (sensitivity only; the registered rule
    is ascending). Membership is tested before any eviction, so the miss counts of a single query do
    not depend on the order, only later evictions do."""
    if warm_start is None:
        warm_start = len(queries) // 2
    cache: OrderedDict[int, None] = OrderedDict()
    seen: set[int] = set()
    touch = cache.move_to_end
    evict = cache.popitem
    add_seen = seen.add
    totals = [0, 0, 0, 0]
    for lo, hi, slot in ((0, warm_start, 0), (warm_start, len(queries), 2)):
        misses = first = 0
        for i in range(lo, hi):
            pages = queries[i]
            for page in reversed(pages) if descending else pages:
                if page in cache:
                    touch(page)
                else:
                    cache[page] = None
                    misses += 1
                    if page not in seen:
                        add_seen(page)
                        first += 1
            n = len(pages)
            while len(cache) > capacity and len(cache) > n:
                evict(last=False)
        totals[slot], totals[slot + 1] = misses, first
    return [totals[0] + totals[2], totals[1] + totals[3], totals[2], totals[3]]


def cache_counts(
    queries: PageSets,
    capacity: int,
    stats: dict[str, Any],
    *,
    shortcut: bool = False,
) -> dict[str, int]:
    """Cache counts at one capacity. When every page the stream ever touches fits in the cache, no
    eviction can occur and misses equal first touches exactly, so the pass is skipped
    (``shortcut``); a test checks this against the full pass."""
    if shortcut and stats["distinct_stream"] <= capacity:
        d_all, d_half = stats["distinct_stream"], stats["distinct_first_half"]
        counts = [d_all, d_all, d_all - d_half, d_all - d_half]
    else:
        counts = lru_pass(queries, capacity)
    return {
        "misses_all": counts[0],
        "first_touch_all": counts[1],
        "misses_warm": counts[2],
        "first_touch_warm": counts[3],
    }


def check_group(stats: dict[str, Any], by_c: dict[int, dict[str, int]], where: str) -> None:
    """Section 9 invariants for one (stream, layout, R) group across the capacities."""
    previous: dict[str, int] | None = None
    for capacity in sorted(by_c):
        row = by_c[capacity]
        touches = stats["pages_sum"]
        if row["misses_all"] > touches or row["misses_warm"] > touches:
            raise InvariantError(f"{where} C={capacity}: misses exceed page touches")
        if row["misses_all"] < stats["distinct_stream"]:
            raise InvariantError(f"{where} C={capacity}: cold misses below distinct pages")
        if (
            row["first_touch_all"] != stats["distinct_stream"]
            or row["first_touch_warm"] != stats["distinct_stream"] - stats["distinct_first_half"]
        ):
            raise InvariantError(f"{where} C={capacity}: first-touch misses depend on C or differ")
        if (
            row["misses_all"] < row["first_touch_all"]
            or row["misses_warm"] < row["first_touch_warm"]
        ):
            raise InvariantError(f"{where} C={capacity}: fewer misses than first touches")
        if previous is not None:
            cap_now = row["misses_warm"] - row["first_touch_warm"]
            cap_before = previous["misses_warm"] - previous["first_touch_warm"]
            all_now = row["misses_all"] - row["first_touch_all"]
            all_before = previous["misses_all"] - previous["first_touch_all"]
            if cap_now > cap_before or all_now > all_before:
                raise InvariantError(f"{where} C={capacity}: capacity misses grew with C")
        previous = row


def simulate_group(
    queries: PageSets, *, shortcut: bool = False, where: str = "", max_pages: int = TOP
) -> tuple[dict[str, Any], dict[str, dict[str, int]], list[int], list[int]]:
    stats, ctx_sum, ctx_distinct = stream_stats(queries, max_pages)
    by_c = {c: cache_counts(queries, c, stats, shortcut=shortcut) for c in CS}
    check_group(stats, by_c, where)
    return stats, {str(c): v for c, v in by_c.items()}, ctx_sum, ctx_distinct


# --- branch locality (trees) ----------------------------------------------------------------------
def branch_locality(branches: Tensor) -> dict[str, Any]:
    """Top-1 branch repeat, shared visited branch, top-1 run lengths and distinct visited branches
    per context, within contexts and across context boundaries (reported separately)."""
    rows = branches.to(torch.int64).tolist()
    same_in = [0, 0]  # [count, pairs]
    same_cross = [0, 0]
    share_in = [0, 0]
    share_cross = [0, 0]
    for i in range(1, len(rows)):
        same = rows[i][0] == rows[i - 1][0]
        share = bool({rows[i][0], rows[i][1]} & {rows[i - 1][0], rows[i - 1][1]})
        s_bucket, h_bucket = (same_in, share_in) if i % CONTEXT else (same_cross, share_cross)
        s_bucket[0] += same
        s_bucket[1] += 1
        h_bucket[0] += share
        h_bucket[1] += 1
    runs = [0] * (CONTEXT + 1)
    visited_total = 0
    for start in range(0, len(rows), CONTEXT):
        block = rows[start : start + CONTEXT]
        run = 1
        for j in range(1, len(block)):
            if block[j][0] == block[j - 1][0]:
                run += 1
            else:
                runs[run] += 1
                run = 1
        runs[run] += 1
        visited_total += len({b for row in block for b in row})
    run_count = sum(runs)
    return {
        "same_top1_within": same_in,
        "same_top1_across": same_cross,
        "share_branch_within": share_in,
        "share_branch_across": share_cross,
        "top1_run_length_hist": runs[1:],
        "top1_runs": run_count,
        "top1_mean_run_length": len(rows) / run_count,
        "distinct_branches_per_context_sum": visited_total,
        "contexts": len(rows) // CONTEXT,
    }


# --- uniform reference (tree: averaged over the visited branch pairs of the trace) ----------------
def uniform_references(
    kind: str, layouts: dict[str, list[int]], branches: Tensor | None
) -> dict[str, dict[str, float]]:
    """E[distinct value pages per query] under uniform draws, per layout and R. Flat: all rows;
    tree: the 512 rows of the query's two visited branches, averaged over the trace's queries."""
    result: dict[str, dict[str, float]] = {}
    pair_counts: Counter[tuple[int, int]] = Counter()
    if branches is not None:
        pair_counts = Counter(core.pair_key(a, b) for a, b in branches.to(torch.int64).tolist())
    for name, positions in layouts.items():
        per_r: dict[str, float] = {}
        for rows in RS:
            if kind == core.FLAT:
                per_r[str(rows)] = core.uniform_flat(rows)
                continue
            total = 0.0
            for pair, count in pair_counts.items():
                total += count * core.expected_distinct_pages(
                    core.branch_pair_rows_per_page(positions, rows, pair), TOP
                )
            per_r[str(rows)] = total / sum(pair_counts.values())
        result[name] = per_r
    return result


# --- SSD-index key reads --------------------------------------------------------------------------
def key_rows_per_page(rows: int) -> int:
    """Key rows (64 B) per page for the page size associated with R (4 KiB for the hypothetical
    R = 1, 2, 8 and for R = 32; 16 KiB for 128; 64 KiB for 512)."""
    return PAGE_BYTES_FOR_R[rows] // KEY_ROW_BYTES


def flat_key_analytic(rows: int, queries: int = QUERIES) -> dict[str, Any]:
    """Flat scans every key page on every query. A key cache smaller than the key store misses all
    of them each query (cyclic scan); one at least as large holds them after the first query."""
    pages = SLOTS // key_rows_per_page(rows)
    per_c = {}
    for capacity in CS:
        if capacity < pages:
            per_c[str(capacity)] = {
                "misses_all": queries * pages,
                "misses_warm": (queries - queries // 2) * pages,
                "first_touch_all": pages,
                "first_touch_warm": 0,
            }
        else:
            per_c[str(capacity)] = {
                "misses_all": pages,
                "misses_warm": 0,
                "first_touch_all": pages,
                "first_touch_warm": 0,
            }
    return {
        "key_pages": pages,
        "key_rows_per_page": key_rows_per_page(rows),
        "label": "analytical",
        "per_query_pages": pages,
        "uncached_amplification": pages * key_rows_per_page(rows) / SLOTS,
        "by_c": per_c,
    }


def tree_key_reads(
    branches: Tensor, key_layouts: dict[str, list[int]], deadline: float | None
) -> dict[str, Any]:
    """Tree key reads, simulated in a separate key cache (actual stream). Keys are laid out by L-ID
    or by each of the three L-RAND permutations; results are per page size, shared by the R values
    that use the same page size."""
    out: dict[str, Any] = {}
    sizes = sorted({PAGE_BYTES_FOR_R[r] for r in RS})
    for size in sizes:
        rows_per_page = size // KEY_ROW_BYTES
        per_layout: dict[str, Any] = {}
        for name in KEY_LAYOUTS:
            if deadline is not None and time.monotonic() > deadline:
                raise CapExceeded("simulation deadline passed during key reads")
            queries = key_page_sets(key_layouts[name], rows_per_page, branches)
            stats, by_c, _, _ = simulate_group(
                queries, where=f"key {name} {size}", max_pages=core.SLOTS // rows_per_page
            )
            per_layout[name] = {
                "stats": stats,
                "by_c": by_c,
                "uncached_amplification": stats["pages_sum"] / len(branches) * rows_per_page / 512,
            }
        out[str(size)] = {"key_rows_per_page": rows_per_page, "layouts": per_layout}
    return out


# --- bootstrap ------------------------------------------------------------------------------------
def bootstrap_indices(contexts: int = CONTEXTS) -> Tensor:
    generator = torch.Generator().manual_seed(BOOTSTRAP_SEED)
    return torch.randint(0, contexts, (BOOTSTRAP_RESAMPLES, contexts), generator=generator)


def bootstrap_interval(context_sums: list[int], indices: Tensor) -> dict[str, float]:
    """Context bootstrap (1,000 resamples) of the per-query mean of an order-free metric. The
    interval is the 26th and 975th of the 1,000 sorted resample means (95% percentile)."""
    per_context = torch.tensor(context_sums, dtype=torch.float64) / CONTEXT
    means = per_context[indices].mean(dim=1).sort().values
    return {
        "mean": float(per_context.mean()),
        "boot_lower": float(means[BOOTSTRAP_RESAMPLES * 25 // 1000]),
        "boot_upper": float(means[BOOTSTRAP_RESAMPLES * 975 // 1000 - 1]),
    }


# --- one checkpoint -------------------------------------------------------------------------------
def simulate_checkpoint(
    *,
    kind: str,
    index: int,
    eval_selected: Tensor,
    eval_branches: Tensor | None,
    calibration_selected: Tensor,
    deadline: float | None = None,
    progress: Callable[[dict[str, Any]], None] | None = None,
    shortcut: bool = False,
) -> dict[str, Any]:
    """The complete per-checkpoint configuration set of section 10. Raises ``CapExceeded`` (with the
    partial record attached as ``.partial``) if ``deadline`` (a ``time.monotonic`` value) passes."""
    started = time.monotonic()
    eval_counts = core.selection_counts(eval_selected)
    layouts = core.build_layouts(kind, core.selection_counts(calibration_selected))
    tree = kind != core.FLAT
    record: dict[str, Any] = {
        "kind": kind,
        "cell_index": index,
        "streams": {},
        "layouts": {name: _layout_fingerprint(pos) for name, pos in layouts.items()},
        "uniform_reference": uniform_references(kind, layouts, eval_branches),
        "evaluation_counts": {"unique_selected_slots": sum(1 for c in eval_counts if c)},
        "bootstrap": {},
        "complete": False,
    }

    def checkpoint_deadline() -> None:
        if deadline is not None and time.monotonic() > deadline:
            error = CapExceeded("simulation deadline passed; partial record preserved")
            error.partial = record  # type: ignore[attr-defined]
            raise error

    queries_n = int(eval_selected.shape[0])
    indices = bootstrap_indices(queries_n // CONTEXT)
    actual_layouts = tuple(layouts)
    order = {
        STREAM_ORDER: core.query_order(STREAM_ORDER, queries_n),
        STREAM_CONTEXT: core.query_order(STREAM_CONTEXT, queries_n),
    }
    fm: dict[str, Tensor] = {}
    record["frequency_matched"] = {}
    for name, seed in zip(STREAMS_FM, FM_SEEDS, strict=True):
        fm[name], record["frequency_matched"][name] = core.frequency_matched_detail(
            eval_counts, seed, index, queries=queries_n
        )
        checkpoint_deadline()
    plan: list[tuple[str, tuple[str, ...]]] = [(STREAM_ACTUAL, actual_layouts)]
    plan += [(s, LAYOUTS_OTHER) for s in (STREAM_ORDER, *STREAMS_FM, STREAM_CONTEXT)]
    base: dict[tuple[str, int], PageSets] = {}
    for stream, names in plan:
        store: dict[str, Any] = record["streams"].setdefault(stream, {})
        for name in names:
            for rows in RS:
                checkpoint_deadline()
                if stream == STREAM_ACTUAL:
                    queries = page_sets(layouts[name], rows, eval_selected)
                    if name in LAYOUTS_OTHER:  # reused by the shuffled streams
                        base[(name, rows)] = queries
                elif stream in order:
                    reference = base.get((name, rows))
                    if reference is None:
                        reference = page_sets(layouts[name], rows, eval_selected)
                        base[(name, rows)] = reference
                    queries = [reference[i] for i in order[stream]]
                else:
                    queries = page_sets(layouts[name], rows, fm[stream])
                where = f"{stream}|{name}|R{rows}"
                stats, by_c, ctx_sum, _ = simulate_group(queries, shortcut=shortcut, where=where)
                store[f"{name}|R{rows}"] = {"stats": stats, "by_c": by_c}
                if stream == STREAM_ACTUAL:
                    record["bootstrap"][f"{name}|R{rows}"] = bootstrap_interval(ctx_sum, indices)
        if progress is not None:
            progress({"stream_done": stream, "elapsed": time.monotonic() - started})
    checkpoint_deadline()
    # Item 10: descending-order sensitivity at the primary setting only (no criterion). The
    # ascending numbers are the registered streams' own, copied unchanged.
    primary_key = f"{LAYOUT_FREQ}|R{core.PRIMARY_R}"
    ascending = record["streams"][STREAM_ACTUAL][primary_key]["by_c"][str(core.PRIMARY_C)]
    counts_desc = lru_pass(base[(LAYOUT_FREQ, core.PRIMARY_R)], core.PRIMARY_C, descending=True)
    record["eviction_order_sensitivity"] = {
        "setting": dict(core.PRIMARY, index="RAM-index"),
        "label": "descriptive sensitivity of the eviction tie order; no criterion",
        "ascending": dict(ascending),
        "descending": dict(
            zip(
                ("misses_all", "first_touch_all", "misses_warm", "first_touch_warm"),
                counts_desc,
                strict=True,
            )
        ),
    }
    if tree:
        assert eval_branches is not None
        record["branch_locality"] = branch_locality(eval_branches)
        key_layouts = {name: layouts[name] for name in KEY_LAYOUTS}
        record["key_reads"] = {
            "tree": tree_key_reads(eval_branches, key_layouts, deadline),
            "flat_analytic_for_reference": {str(r): flat_key_analytic(r, queries_n) for r in RS},
        }
    else:
        record["key_reads"] = {"flat": {str(r): flat_key_analytic(r, queries_n) for r in RS}}
    record["complete"] = True
    record["seconds"] = time.monotonic() - started
    return record


def _layout_fingerprint(positions: list[int]) -> dict[str, Any]:
    from .io import sha256

    return {
        "permutation": core.is_permutation(positions),
        "sha256": sha256(",".join(map(str, positions)).encode()),
    }


def config_count(kind: str) -> int:
    """Number of (stream, layout, R, C) page-cache simulations of section 10 for one checkpoint."""
    layouts = len(core.layouts_for(kind))
    others = len(LAYOUTS_OTHER) * len((STREAM_ORDER, *STREAMS_FM, STREAM_CONTEXT))
    return (layouts + others) * len(RS) * len(CS)


# Silence unused-import lint for names kept for documentation of the registered set.
_ = (SLOTS, BRANCHES, LAYOUT_ID, LAYOUT_FREQ)
