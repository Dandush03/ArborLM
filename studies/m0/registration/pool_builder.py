# ruff: noqa: E501
"""ADR-0033 addendum 1, section 10 part B: the per-cluster pool builder (decided, section 13 item 6 (a)).

``studies/m0/core.py::generate_pool`` gives every LINEAGE an equal quota. With lineages merged into clusters
that is not "balanced over the G clusters" (line 388) or "spread evenly over the G clusters" (line 390). This
builder gives every CLUSTER an equal quota and divides it inside the cluster. The items of the text:

1. Clusters: the global clusters assigned to the part that have at least one registered lineage of the
   evaluation, in increasing code-point order of identity (``clusters_in_order``).
2. Cluster quotas: the size divided equally over those clusters by ``core.allocate`` (largest remainder, ties
   to the earlier cluster).
3. Levels inside a cluster: the cluster's quota divided over the levels of the mix, in increasing level
   order, by ``core.allocate`` with the mix as weights.
4. Lineages inside a cluster and level: that count divided equally over the cluster's registered lineages of
   the evaluation, in increasing order of id, by ``core.allocate``. A lineage draws its shapes as its own
   generator already does.
5. Streams: ``stream(seed, role, salt_label, e, p, lineage id, str(level))``, as ``generate_pool`` has it.
   A lineage's stream does not depend on which cluster it sits in.
6. Uniqueness and order: an item is rejected if its NORMALISED TEXT (``core.text_hash``) is already in
   ``taken`` (earlier roles and earlier in this pool); generation runs over clusters, then levels, then
   lineages, in the orders above, so the shared set is deterministic. A quota a lineage cannot fill is a
   capacity failure (``CapacityShortfall``, or recorded in ``shortfalls``) and is never moved to a sibling
   lineage or cluster. (The capacity count of stage 4 does not use this set.)
7. The M0 draw (``m0_draw_by_cluster``): the 1,500 divided equally over the part's clusters, then equally
   over each cluster's registered lineages, by ``core.allocate`` in the same orders; each lineage's items
   sampled from its development items with ``stream(400006, "m0-draw", lineage id)`` as ``core.m0_draw`` does.
8. The record: every item carries its global cluster identity (``PoolItem.cluster``); ``summarise`` gives
   counts per family, cluster, lineage and level, and the pool hash.

Nothing here runs on real lineages until the freeze calls it; it reads no file and no map. ``registered``
is ``{cluster id: [registered lineage ids of the evaluation]}`` for one evaluation and part (the form of
``registered`` in the stage-4 record), ``lineage_of`` maps an id to its ``Lineage``.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from studies.m0.core import Item, Lineage, allocate, draw_items, stream, text_hash


class CapacityShortfall(RuntimeError):
    """A lineage could not fill its quota at a level: a capacity failure, never repaired by moving the quota."""


@dataclass(frozen=True)
class PoolItem:
    """A pool item: the fields of ``core.Item`` plus the global cluster identity (item 8)."""

    id: str
    eval: str
    part: str
    lineage: str
    family: str
    level: int
    question: str
    structured: dict[str, Any]
    answer: str
    answer_type: str
    k: int | None
    cluster: str

    def to_json(self) -> str:
        return json.dumps(self.__dict__, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _with_cluster(it: Item, cluster: str) -> PoolItem:
    return PoolItem(it.id, it.eval, it.part, it.lineage, it.family, it.level, it.question, it.structured,
                    it.answer, it.answer_type, it.k, cluster)


def clusters_in_order(registered: Mapping[str, Sequence[str]]) -> list[str]:
    """Item 1: the clusters with at least one registered lineage, in increasing code-point order."""
    return sorted(c for c, lins in registered.items() if lins)


def plan_pool(
    registered: Mapping[str, Sequence[str]], size: int, level_mix: Mapping[int, float]
) -> list[tuple[str, int, str, int]]:
    """Items 1 to 4 as a table: (cluster, level, lineage, count), in generation order (cluster, level, lineage)."""
    clusters = clusters_in_order(registered)
    if not clusters:
        return []
    levels = sorted(level_mix)
    plan: list[tuple[str, int, str, int]] = []
    for c, quota in zip(clusters, allocate(size, [1.0] * len(clusters)), strict=True):
        lins = sorted(registered[c])
        for lv, n_level in zip(levels, allocate(quota, [level_mix[lv] for lv in levels]), strict=True):
            for x, n in zip(lins, allocate(n_level, [1.0] * len(lins)), strict=True):
                plan.append((c, lv, x, n))
    return plan


def build_pool(
    registered: Mapping[str, Sequence[str]],
    lineage_of: Callable[[str], Lineage],
    eval_id: str,
    part: str,
    role: str,
    seed: int,
    size: int,
    level_mix: Mapping[int, float],
    taken: set[str],
    salt_label: str = "",
    shortfalls: list[tuple[str, int, int, int]] | None = None,
) -> list[PoolItem]:
    """The pool of ``size`` items of one evaluation part, balanced over its clusters (section 10 part B).

    ``taken`` holds the text hashes already used by earlier roles and is updated. A quota a lineage cannot
    fill raises ``CapacityShortfall``; with ``shortfalls`` given it is appended as (lineage, level, wanted,
    supplied) and the pool is short by that much (``generate_pool``'s own convention).
    """
    out: list[PoolItem] = []
    for cluster, lv, x, n in plan_pool(registered, size, level_mix):
        if n == 0:
            continue
        lin = lineage_of(x)
        if lin.eval != eval_id:
            raise ValueError(f"lineage {x} is not of evaluation {eval_id}")
        rng = stream(seed, role, salt_label, eval_id, part, x, str(lv))
        got = draw_items(lin, part, lv, n, rng, taken, role, allow_short=True)
        if len(got) < n:
            if shortfalls is None:
                raise CapacityShortfall(f"{x} level {lv}: wanted {n} items, supplied {len(got)}")
            shortfalls.append((x, lv, n, len(got)))
        out.extend(_with_cluster(it, cluster) for it in got)
    return out


def m0_draw_by_cluster(
    pool: Sequence[PoolItem],
    registered: Mapping[str, Sequence[str]],
    size: int = 1500,
    seed: int = 400006,
    allow_short: bool = False,
) -> list[PoolItem]:
    """Item 7: ``size`` items of the development pool, equal per cluster, then equal per registered lineage."""
    by_lineage: dict[str, list[PoolItem]] = {}
    for it in pool:
        by_lineage.setdefault(it.lineage, []).append(it)
    clusters = clusters_in_order(registered)
    out: list[PoolItem] = []
    if not clusters:
        return out
    for c, quota in zip(clusters, allocate(size, [1.0] * len(clusters)), strict=True):
        lins = sorted(registered[c])
        for x, q in zip(lins, allocate(quota, [1.0] * len(lins)), strict=True):
            members = by_lineage.get(x, [])[:]
            if q > len(members):
                if not allow_short:
                    raise ValueError(f"lineage {x} has {len(members)} development items, quota {q}")
                q = len(members)
            out.extend(stream(seed, "m0-draw", x).sample(members, q))
    return out


def pool_hash(items: Sequence[PoolItem]) -> str:
    h = hashlib.sha256()
    for it in items:
        h.update(it.to_json().encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


@dataclass
class PoolRecord:
    eval: str
    part: str
    role: str
    size: int
    sha256: str
    per_cluster: dict[str, int] = field(default_factory=dict)
    per_lineage: dict[str, int] = field(default_factory=dict)
    per_level: dict[int, int] = field(default_factory=dict)
    per_family: dict[str, int] = field(default_factory=dict)
    per_cluster_level: dict[str, dict[int, int]] = field(default_factory=dict)


def summarise(items: Sequence[PoolItem], eval_id: str, part: str, role: str) -> PoolRecord:
    """Item 8: counts per family, cluster, lineage and level (and cluster by level), and the hash."""
    rec = PoolRecord(eval_id, part, role, len(items), pool_hash(items))
    for it in items:
        rec.per_cluster[it.cluster] = rec.per_cluster.get(it.cluster, 0) + 1
        rec.per_lineage[it.lineage] = rec.per_lineage.get(it.lineage, 0) + 1
        rec.per_level[it.level] = rec.per_level.get(it.level, 0) + 1
        rec.per_family[it.family] = rec.per_family.get(it.family, 0) + 1
        cl = rec.per_cluster_level.setdefault(it.cluster, {})
        cl[it.level] = cl.get(it.level, 0) + 1
    return rec


def check_disjoint(pools: Mapping[str, Sequence[PoolItem]]) -> list[str]:
    """Problems: an item repeated within a pool or shared between pools, by normalised text (as core does)."""
    seen: dict[str, str] = {}
    problems: list[str] = []
    for name in sorted(pools):
        for it in pools[name]:
            h = text_hash(it.question)
            if h in seen:
                problems.append(f"{it.id} ({name}) repeats an item of {seen[h]}")
            else:
                seen[h] = name
    return problems
