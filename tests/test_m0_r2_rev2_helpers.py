# ruff: noqa: E501
"""Helpers for the R2 rev2 tests: draw items from the batch-1 (old) shape and from the rev2 shape of one lineage. Self-checked only."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from studies.m0.core import Item, build_item, lineages_of, stream
from studies.m0.lineages_r2_common import load_batch1
from studies.m0.lineages_r2_rev2 import load_rev2

OLD = {x.id: x for x in load_batch1()}
CORE = {x.id: x for x in lineages_of("R2")}
NEW = {x.id: x for x in load_rev2()}


def draw(lin, level: int, n: int, tag: str = "t") -> list[Item]:  # type: ignore[no-untyped-def]
    r = stream(954001, "rev2-test", lin.id, str(level), tag)
    return [build_item(lin, level, r, "A", f"t/{level}/{i}") for i in range(n)]


def share(items: list[Item], f: Callable[[dict[str, Any]], bool | None]) -> float:
    vals = [f(it.structured) for it in items]
    vals = [v for v in vals if v is not None]
    return sum(vals) / len(vals)


def acc(items: list[Item], guess: Callable[[dict[str, Any]], str | None]) -> float:
    hit = tot = 0
    for it in items:
        g = guess(it.structured)
        if g is None:
            continue
        tot += 1
        hit += g == it.answer
    return hit / tot
