# ruff: noqa: E501
"""Shared pieces of the R2 batch-1 lineages (lineage repair, strict reading of "distinct solution procedure").

The batch has its OWN registry (``BATCH1``), not ``core.REGISTRY``: the lineages have no second solvers yet and the
existing suite parametrises over the core registry. Ids are ``R2.<function name>``. No intended part is assigned here: the
registered partition is by seed over the final family list (ADR-0033 section 6.4).

Authoring rule applied (lead ruling, strict): a lineage is a general ALGORITHM. Changing the number system, constraint mix,
final question, names, order, negation or surface frame is a SHAPE of one lineage, never a new one. Each builder's docstring
names its procedure and the shapes it draws; the manifest log records what was rejected as a duplicate.
"""

from __future__ import annotations

import importlib
import json
import random
from collections.abc import Callable
from typing import TypeVar

from studies.m0.core import ALL_LEVELS, Built, Lineage, Retry, build_item, lineages_of, stream

T = TypeVar("T")

BATCH1: list[Lineage] = []
FAMILY_MODULES = (
    "dynprog", "numtheory", "structures", "parsing", "greedy", "graphs",
    "games", "dynamics", "codes", "combinatorics", "search", "strings",
)

Builder = Callable[[int, random.Random], Built]


def batch1(family: str) -> Callable[[Builder], Builder]:
    def deco(fn: Builder) -> Builder:
        lid = f"R2.{fn.__name__}"
        if any(x.id == lid for x in BATCH1) or any(x.id == lid for x in lineages_of("R2")):
            raise ValueError(f"duplicate lineage id {lid}")
        BATCH1.append(Lineage(lid, "R2", family, fn))
        return fn

    return deco


def load_batch1() -> list[Lineage]:
    for fam in FAMILY_MODULES:
        importlib.import_module(f"studies.m0.lineages_r2_{fam}")
    return sorted(BATCH1, key=lambda x: x.id)


def until(tries: int, make: Callable[[], T], ok: Callable[[T], bool]) -> T:
    """Draw ``make()`` until ``ok`` holds, inside one build (so a wanted share is hit exactly and the accepted items are not
    biased by how often each kind of draw is accepted); Retry when ``tries`` draws all fail."""
    for _ in range(tries):
        v = make()
        if ok(v):
            return v
    raise Retry


def lst(xs: list[int]) -> str:
    return ", ".join(str(x) for x in xs)


def and_(xs: list[str]) -> str:
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]


def check_family_r2(family: str, per_level: int = 40) -> list[str]:
    """Mechanical checks on every batch-1 lineage of one family; returns problems (empty when none). No independent solver exists yet:
    these check builds, grammar, JSON stability, absence of the key in the structured form, determinism and answer variety."""
    from studies.m0.scoring import in_grammar, normalise_answer

    problems: list[str] = []
    lins = [x for x in load_batch1() if x.family == family]
    if not lins:
        return [f"no batch-1 lineage in family {family}"]
    for lin in lins:
        for lv in ALL_LEVELS:
            items = []
            r = stream(953702, "family-check", lin.id, str(lv))
            for i in range(per_level):
                items.append(build_item(lin, lv, r, "A", f"{lin.id}/{lv}/{i}"))
            first = build_item(lin, lv, stream(953702, "family-check", lin.id, str(lv)), "A", "d")
            if first.question != items[0].question or first.answer != items[0].answer:
                problems.append(f"{lin.id} L{lv}: not deterministic")
            if len({it.question for it in items}) < 0.9 * per_level:
                problems.append(f"{lin.id} L{lv}: fewer than 90% distinct questions")
            for it in items:
                if not in_grammar(it.answer_type, normalise_answer(it.answer)):
                    problems.append(f"{it.id}: answer {it.answer!r} not in grammar {it.answer_type}")
                if it.k is not None and it.k < 2:
                    problems.append(f"{it.id}: k < 2")
                if it.answer_type == "name" and it.answer not in it.question:
                    problems.append(f"{it.id}: closed answer {it.answer!r} not named in the question")
                if json.loads(json.dumps(it.structured)) != it.structured:
                    problems.append(f"{it.id}: structured form is not JSON-stable")
                if "answer" in it.structured or "key" in it.structured:
                    problems.append(f"{it.id}: structured form carries the key")
            if items[0].answer_type in ("yn", "ynu") and lv >= 1 and len({it.answer for it in items}) < 2:
                problems.append(f"{lin.id} L{lv}: only one answer in {per_level} items")
    return problems
