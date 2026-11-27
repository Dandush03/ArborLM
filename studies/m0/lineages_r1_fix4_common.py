# ruff: noqa: E501
"""Registry and helpers of the R1 fix-round-4 shapes (ids end in ``_r6``; the human lead's fifth decision, lead rulings R-24 to R-29).

Round 4 repairs one thing only in the shapes it rewrites: LEVELS. Each ``_r6`` builder is the earlier builder with a level parameter that changes at every level (so that two
levels never produce the same stream of items) and that makes the item longer or larger as the level rises; the solution procedure, the answer rule and the statement
conventions are unchanged. No shape is authored here that is not a repaired earlier shape (R-25). Shapes live in their OWN list (``FIX4``), not in ``core.REGISTRY`` (R-9).
"""

from __future__ import annotations

import importlib
import random
from collections.abc import Callable

from studies.m0.core import Built, Lineage

FIX4: list[Lineage] = []
REPLACES: dict[str, str] = {}
MODULES = ("a",)
Builder = Callable[[int, random.Random], Built]


def fix4(family: str, replaces: str) -> Callable[[Builder], Builder]:
    def deco(fn: Builder) -> Builder:
        lid = f"R1.{fn.__name__}"
        if any(x.id == lid for x in FIX4):
            raise ValueError(f"duplicate lineage id {lid}")
        FIX4.append(Lineage(lid, "R1", family, fn))
        REPLACES[lid] = replaces
        return fn

    return deco


def load_fix4() -> list[Lineage]:
    for m in MODULES:
        importlib.import_module(f"studies.m0.lineages_r1_fix4_{m}")
    return sorted(FIX4, key=lambda x: x.id)
