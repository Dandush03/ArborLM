# ruff: noqa: E501
"""P9 page-cache simulator for general N (package I4): LRU page misses, cache rule, count-preserving
nulls with ADR-0016's identity null, pages per query and cross-query reuse, planted-trace generator and
the key-traffic identity.

Specification: ADR-0017 section 8.4 (simulator, traces, cache rule, E), 9 (synthetic part, D09 sweep,
key traffic). STUB: signatures only.

Required before use (ADR 8.4): exact equivalence with P7-B on P7-B's recorded traces at 4,096 slots
(``p7b_equivalence``) and a sparse co-access count (``layout.sparse_coaccess``). Simulated misses are
a logical simulation of an LRU page cache, never storage I/O; the key-traffic result is an arithmetic
identity (ADR 5.2), labelled as such.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .core import Cell, SimRecord, Trace
from .layout import Layout

if TYPE_CHECKING:
    from torch import Tensor


def working_set(calibration: Trace) -> int:
    """W: the number of distinct slots selected on the calibration stream for this trace type
    (computed separately for answer-site and all-position traces, ADR 8.4)."""
    raise NotImplementedError


def cache_pages(working: int, rows: int, rho: float) -> int:
    """C = max(1, round(rho * W / R)) (ADR 8.4)."""
    raise NotImplementedError


def page_sequence(trace: Trace, layout: Layout, rows: int) -> "Tensor":
    """``[Q, 8] int64`` page ids of every query's selected slots under ``layout`` at ``rows`` per page."""
    raise NotImplementedError


def lru_misses(pages: "Tensor", cache_pages_count: int, tie: str, *, warm_queries: int = 0) -> int:
    """Number of LRU misses of the page-id sequence ``pages [Q, 8]`` with ``cache_pages_count`` pages.
    ``tie`` in ``core.TIE_RULES`` orders the pages of one query (ascending or descending page id)
    before they are looked up, as P7-B does. ``warm_queries`` initial queries fill the cache without
    being counted. Must equal ``arborlm.p7b_sim`` on the P7-B traces at 4,096 slots."""
    raise NotImplementedError


def count_preserving_null(trace: Trace, replicate_seed: int) -> Trace:
    """A null trace with the same per-slot access counts and per-query set sizes, with slot sharing
    across queries randomized (seeded), keeping the structure ADR-0016 describes; for single-set
    streams the identity null (the trace itself) applies (ADR 8.4 and ADR-0016)."""
    raise NotImplementedError


def pages_per_query(pages: "Tensor") -> float:
    """Mean number of distinct pages touched by one query (within-query co-selection, reported
    separately from cross-query reuse, ADR 8.4)."""
    raise NotImplementedError


def cross_query_reuse(pages: "Tensor", window: int) -> float:
    """Fraction of a query's pages already touched by one of the previous ``window`` queries."""
    raise NotImplementedError


def e_ratio(actual: int, nulls: list[int]) -> float | None:
    """E = actual misses / mean of the count-preserving nulls; None when the mean is 0."""
    raise NotImplementedError


def is_degenerate(null_miss_rate: float, single_set: bool) -> bool:
    """DEGENERATE: null miss rate below ``core.E_NULL_FLOOR`` (0.05), or a single-set stream."""
    raise NotImplementedError


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
) -> SimRecord:
    """One (trace, layout, R, rho, tie) setting: W from ``calibration``, C from ``cache_pages``,
    actual misses, three nulls, E, null miss rate, pages per query and cross-query reuse."""
    raise NotImplementedError


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
    descriptive), for the actual layout and the control layouts; writes ``core.sim_path``."""
    raise NotImplementedError


def p7b_equivalence(traces_dir: Path) -> dict[str, Any]:
    """Check exact equality with the P7-B simulator on P7-B's recorded traces at 4,096 slots (the
    required equivalence gate before the simulator is used). Returns a record with the counts compared
    and ``passed``."""
    raise NotImplementedError


# --- synthetic part (ADR 9) -------------------------------------------------------------------------------
PLANTED_KINDS = (
    "popularity_only",  # E ~ 1
    "clusters_random_sharing",
    "clusters_aligned_sharing",
    "collapsed_single_set",  # identity null, DEGENERATE
    "working_set_below_cache",  # DEGENERATE
    "incomplete_input",  # INCOMPLETE
)


@dataclass
class PlantedTrace:
    """A generated trace with the class it must receive: ``expected`` in {"E~1", "LOCALITY_POSITIVE",
    "NO_DIFFERENCE", "DEGENERATE", "INCOMPLETE"}, plus the calibration trace and the cluster labels."""

    kind: str
    trace: Trace | None
    calibration: Trace | None
    expected: str


def planted_trace(kind: str, *, slots: int, seed: int) -> PlantedTrace:
    """Generate the planted-structure trace of ``kind`` with known answers (ADR 9)."""
    raise NotImplementedError


def key_traffic(arch: str, slots: int, key_width: int, queries: int) -> dict[str, int | str]:
    """Key traffic with keys in RAM (zero) against keys on storage (flat reads every key page; the tree
    reads the router and two branches): an arithmetic identity from ``core.logical_key_products``,
    labelled ``"identity"``, not a simulation result (ADR 9)."""
    raise NotImplementedError


def main(argv: list[str] | None = None) -> int:
    """CLI ``uv run --locked python -m studies.p9.sim {cell,stage,equivalence,planted} ...``."""
    raise NotImplementedError
