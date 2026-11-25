# ruff: noqa: E501
"""Shared pieces of the R1 pilot lineages (lineage repair, pilot batch 1).

The pilot lineages are kept in their OWN registry (``PILOT``), not in ``core.REGISTRY``: they have no second solvers yet, and
the existing suite parametrises over the core registry. Ids are ``R1.<function name>`` so that registration later changes
nothing in the ids the solver agent sees. ``INTENDED_PART`` is the part I intend; the registered partition is by seed over
the final family list (ADR-0033 section 6.4) and may differ.
"""

from __future__ import annotations

import importlib
import random
from collections.abc import Callable

from studies.m0.core import Built, Lineage, lineages_of

PILOT: list[Lineage] = []
INTENDED_PART: dict[str, str] = {}
FAMILY_MODULES = (
    "temporal", "spatial", "containers", "elimination", "boolean_state",
    "order", "graph", "equivalence", "tracking", "conditional", "categories", "kinship",
)
YNU = ("yes", "no", "cannot be determined")

EXTRA_MODULES = ("rev2", "new2", "rev3")  # shape revisions (and, later, further new lineages): imported by load_pilot, not tied to one family
Builder = Callable[[int, random.Random], Built]


def pilot(family: str, part: str) -> Callable[[Builder], Builder]:
    def deco(fn: Builder) -> Builder:
        lid = f"R1.{fn.__name__}"
        if any(x.id == lid for x in PILOT) or any(x.id == lid for x in lineages_of("R1")):
            raise ValueError(f"duplicate lineage id {lid}")
        PILOT.append(Lineage(lid, "R1", family, fn))
        INTENDED_PART[lid] = part
        return fn

    return deco


def pl(n: int, word: str) -> str:
    """'1 block', '2 blocks'."""
    return f"{n} {word}" + ("" if n == 1 else "s")


def and_(xs: list[str]) -> str:
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]


def load_pilot() -> list[Lineage]:
    for fam in (*FAMILY_MODULES, *EXTRA_MODULES):
        importlib.import_module(f"studies.m0.lineages_r1_{fam}")
    return sorted(PILOT, key=lambda x: x.id)
