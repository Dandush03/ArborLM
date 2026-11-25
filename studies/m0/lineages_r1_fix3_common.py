# ruff: noqa: E501
"""Registry and helpers of the R1 fix-round-3 shapes (ids end in ``_r5``; the human lead's fourth decision, lead rulings R-1 to R-17).

Shapes here live in their OWN list (``FIX3``), not in ``core.REGISTRY`` (ruling R-9). ``REPLACES`` maps each shape to the id it replaces in
``lineages_r1_clusters_v2.registered_v2()``. Two construction rules hold for every shape (rulings R-1, R-13): nothing is redrawn because of a
heuristic's outcome or because of the answer value; the answer (or the answer class) is DRAWN FIRST where it is balanced, and the item is built to meet it.
A ``Retry`` is raised only for validity (a unique answer, a non-empty candidate set).
"""

from __future__ import annotations

import importlib
import random
from collections.abc import Callable

from studies.m0.core import Built, Lineage

FIX3: list[Lineage] = []
REPLACES: dict[str, str] = {}
MODULES = ("a", "b", "c", "d", "e")
Builder = Callable[[int, random.Random], Built]
YNU = ("yes", "no", "cannot be determined")


def fix3(family: str, replaces: str) -> Callable[[Builder], Builder]:
    def deco(fn: Builder) -> Builder:
        lid = f"R1.{fn.__name__}"
        if any(x.id == lid for x in FIX3):
            raise ValueError(f"duplicate lineage id {lid}")
        FIX3.append(Lineage(lid, "R1", family, fn))
        REPLACES[lid] = replaces
        return fn

    return deco


def load_fix3() -> list[Lineage]:
    for m in MODULES:
        try:
            importlib.import_module(f"studies.m0.lineages_r1_fix3_{m}")
        except ModuleNotFoundError as e:  # a module of this round not written yet
            if e.name != f"studies.m0.lineages_r1_fix3_{m}":
                raise
    return sorted(FIX3, key=lambda x: x.id)
