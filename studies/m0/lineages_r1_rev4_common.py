# ruff: noqa: E501
"""Registry and helpers of the R1 revision-4 shapes (second audit, lead rulings R-1 to R-9 of docs/reviews/m0-lineage-decision-2026-11-25/LEAD_RULINGS_2.md).

Revision-4 shapes live in their OWN list (``REV4``), not in ``lineages_r1_common.PILOT`` and not in ``core.REGISTRY`` (ruling R-9: nothing is registered before a second audit).
Every shape id ends in ``_r4``. ``REPLACES`` maps each shape to the registered shape (the id in ``lineages_r1_clusters.registered_lineages()``) that it would replace.
No shape here conditions its items on the outcome of a heuristic (ruling R-1): where a tell is removed it is removed by the way the item is built (a planted solution,
a symmetric sign multiset, a threshold set from the computed margin, a bracket round chosen first, ...), as each docstring says.
"""

from __future__ import annotations

import importlib
import random
from collections.abc import Callable

from studies.m0.core import Built, Lineage, lineages_of

REV4: list[Lineage] = []
REPLACES: dict[str, str] = {}
MODULES = ("rev4", "rev4_b", "rev4_c")
Builder = Callable[[int, random.Random], Built]


def rev4(family: str, replaces: str) -> Callable[[Builder], Builder]:
    def deco(fn: Builder) -> Builder:
        lid = f"R1.{fn.__name__}"
        if any(x.id == lid for x in REV4) or any(x.id == lid for x in lineages_of("R1")):
            raise ValueError(f"duplicate lineage id {lid}")
        REV4.append(Lineage(lid, "R1", family, fn))
        REPLACES[lid] = replaces
        return fn

    return deco


def load_rev4() -> list[Lineage]:
    for m in MODULES:
        try:
            importlib.import_module(f"studies.m0.lineages_r1_{m}")
        except ModuleNotFoundError as e:  # a module of this revision not written yet
            if e.name != f"studies.m0.lineages_r1_{m}":
                raise
    return sorted(REV4, key=lambda x: x.id)
