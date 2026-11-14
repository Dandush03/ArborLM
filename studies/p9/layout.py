# ruff: noqa: E501
"""P9 physical layouts for general N (package I4): identity, frequency packing, sparse co-access,
random partition, branch-constrained co-access and the oracle cluster layout.

Specification: ADR-0017 section 8.4 (comparison layouts, oracle layout, calibration-only fitting).
STUB: signatures only. Layouts are fitted on a **calibration** trace only and applied to evaluation
traces; ``require_calibration`` is the guard. The P7-B layout code fixes 4,096 slots, uses a dense
co-access matrix (16 GiB at 65,536) and 16-bit layout files, so it is re-implemented here with a sparse
co-access count and 32-bit files; nothing in ``arborlm`` is modified.

Conventions: a ``Layout`` stores ``order [N] int64`` with ``order[p]`` the slot at position ``p``; the
page of slot ``s`` at ``R`` rows per page is ``position_of[s] // R``.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .core import Trace

if TYPE_CHECKING:
    from torch import Tensor

LAYOUT_NAMES = (
    "identity",
    "frequency",
    "coaccess",
    "random_partition",
    "branch_coaccess",
    "oracle_cluster",
)


@dataclass
class Layout:
    """A slot-to-position permutation. ``name`` in ``LAYOUT_NAMES``; ``rows`` is the rows-per-page the
    layout was fitted for (None when it does not depend on R); ``info`` records fit statistics."""

    name: str
    rows: int | None
    order: "Tensor"
    info: dict[str, Any] = field(default_factory=dict)

    def positions(self) -> "Tensor":
        """``[N] int64`` inverse permutation: position of each slot."""
        raise NotImplementedError

    def key(self) -> str:
        """``name`` or ``name@R``; the key used in ``SimRecord.layout``."""
        raise NotImplementedError


@dataclass
class SparseCoaccess:
    """Pair counts of slots selected together by one query (and the per-slot access counts), stored
    sparsely: ``pairs [M, 2] int64`` with ``pairs[:, 0] < pairs[:, 1]``, ``counts [M] int64``,
    ``frequency [N] int64``. Memory is O(M), never O(N^2)."""

    slots: int
    pairs: "Tensor"
    counts: "Tensor"
    frequency: "Tensor"


def require_calibration(trace: Trace) -> Trace:
    """Return ``trace`` if its stream is ``calibration`` and refuse an evaluation stream (layouts are
    fitted on the calibration stream only, ADR 8.4)."""
    raise NotImplementedError


def sparse_coaccess(trace: Trace) -> SparseCoaccess:
    """Count co-selected slot pairs and per-slot frequencies in ``trace.selected [Q, 8]``."""
    raise NotImplementedError


def identity_layout(slots: int) -> Layout:
    raise NotImplementedError


def frequency_layout(calibration: Trace) -> Layout:
    """Slots sorted by calibration access count descending, ties by slot id."""
    raise NotImplementedError


def coaccess_layout(calibration: Trace, rows: int, *, seed: int, refine_rounds: int = 2) -> Layout:
    """Optimized co-access layout for ``rows`` slots per page fitted on ``calibration``, unconstrained
    for flat and tree alike (ADR 8.4): greedy page filling by pair affinity then bounded refinement,
    deterministic given ``seed``. Slots never accessed are placed last in id order."""
    raise NotImplementedError


def random_partition_layout(slots: int, rows: int, seed: int) -> Layout:
    """Seeded random permutation (a random partition into pages)."""
    raise NotImplementedError


def branch_coaccess_layout(
    calibration: Trace, rows: int, *, branches: int, per_branch: int, seed: int
) -> Layout:
    """Tree control: each branch's ``per_branch`` slots contiguous (branch ``b`` owns slots
    ``b * per_branch ..``); co-access order inside and across branches. Reported as a control only."""
    raise NotImplementedError


def oracle_cluster_layout(calibration: Trace, clusters: int) -> Layout:
    """Bound (ADR 8.4): each slot goes to the cluster with most of its calibration accesses (ties to
    the lowest cluster number), clusters contiguous, within a cluster by slot id; never-accessed
    slots last. Uses ``calibration.cluster`` (queries with -1 are ignored)."""
    raise NotImplementedError


def build_layouts(
    calibration: Trace,
    rows_list: tuple[int, ...],
    *,
    arch: str,
    seed: int,
    clusters: int,
    branches: int = 0,
    per_branch: int = 0,
) -> dict[str, Layout]:
    """All layouts a cell needs, keyed by ``Layout.key()``: identity, frequency, co-access and random
    partition per R in ``rows_list``, the oracle cluster layout, and (trees) the branch-constrained
    co-access layout. Every layout is verified with ``verify_layout``."""
    raise NotImplementedError


def verify_layout(layout: Layout, slots: int, groups: list[list[int]] | None = None) -> None:
    """Raise unless ``layout.order`` is a permutation of ``range(slots)`` (and each of ``groups`` is
    contiguous when given)."""
    raise NotImplementedError


def write_layouts(path: Path, layouts: dict[str, Layout]) -> dict[str, str]:
    """Write 32-bit layout files with an index; returns key -> SHA-256 of the layout's order."""
    raise NotImplementedError


def read_layouts(path: Path, expected: dict[str, str] | None = None) -> dict[str, Layout]:
    raise NotImplementedError
