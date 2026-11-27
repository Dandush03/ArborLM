# ruff: noqa: E501
"""Shared pieces of the M1 batch-1 lineages (strict reading: one lineage = one general solution algorithm).

The batch has its OWN registry (``BATCH``), not ``core.REGISTRY``: these lineages have no second solvers yet. Ids are ``M1.<function name>`` and must not
collide with the ids of the sixteen existing M1 lineages. Every question states the answer format inside the item; every answer is a plain number
(integer, or a decimal with at most two places and no trailing zeros) of ``answer_type`` "number" with ``k = None``.
"""

from __future__ import annotations

import importlib
import json
import random
from collections.abc import Callable

from studies.m0.core import ALL_LEVELS, Built, Lineage, build_item, lineages_of, stream

BATCH: list[Lineage] = []
FIRMNESS: dict[str, str] = {}  # lineage id -> "firm" | "borderline" (my own judgement against the strict reading)
FAMILY_MODULES = ("number_theory", "counting", "statistics", "sequences", "algebra", "geometry", "pricing", "division")

WHOLE = "Answer with a whole number."
DECIMAL = "Answer with a number; if it is not whole, write it as a decimal with no more than two decimal places and no trailing zeros."

Builder = Callable[[int, random.Random], Built]


def m1(family: str, firmness: str = "firm") -> Callable[[Builder], Builder]:
    def deco(fn: Builder) -> Builder:
        lid = f"M1.{fn.__name__}"
        if any(x.id == lid for x in BATCH) or any(x.id == lid for x in lineages_of("M1")):
            raise ValueError(f"duplicate lineage id {lid}")
        BATCH.append(Lineage(lid, "M1", family, fn))
        FIRMNESS[lid] = firmness
        return fn

    return deco


def ctx(r: random.Random) -> str:
    """A one-sentence setting (name, town, one of four wordings) put before questions whose numbers alone give a small parameter space. It is surface frame only: it adds
    wording variety (so the text-level capacity gate can pass) and NO structural variety; the manifest reports the name-free structured counts beside it."""
    from studies.m0.vocab import NAMES, TOWNS

    n, t = r.choice(NAMES), r.choice(TOWNS)
    return r.choice((f"{n} from {t} found this problem in a puzzle book.", f"This problem comes from a quiz held in {t}, set by {n}.", f"{n} of {t} wrote this problem for a maths club.", f"At a maths club in {t}, {n} is asked this."))


def pl(n: int, word: str) -> str:
    return f"{n} {word}" + ("" if n == 1 else "s")


def and_(xs: list[str]) -> str:
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]


def load_batch() -> list[Lineage]:
    for fam in FAMILY_MODULES:
        importlib.import_module(f"studies.m0.lineages_m1_{fam}")
    return sorted(BATCH, key=lambda x: x.id)


def check_family(family: str, per_level: int = 40) -> list[str]:
    """Mechanical checks of every batch lineage of one family (no independent solver exists yet; these do not check the key against one):
    builds succeed, answers are in the number grammar, the question states an answer format, the structured form is JSON-stable and does not carry
    the key, generation is deterministic, and questions are mostly distinct."""
    from studies.m0.scoring import in_grammar, normalise_answer

    problems: list[str] = []
    lins = [x for x in load_batch() if x.family == family]
    if not lins:
        return [f"no batch lineage in family {family}"]
    for lin in lins:
        for lv in ALL_LEVELS:
            items = [build_item(lin, lv, r, "A", f"{lin.id}/{lv}/{i}") for r in [stream(953702, "family-check", lin.id, str(lv))] for i in range(per_level)]
            first = build_item(lin, lv, stream(953702, "family-check", lin.id, str(lv)), "A", "d")
            if first.question != items[0].question:
                problems.append(f"{lin.id} L{lv}: not deterministic")
            if len({it.question for it in items}) < 0.9 * per_level:
                problems.append(f"{lin.id} L{lv}: fewer than 90% distinct questions")
            for it in items:
                if it.answer_type != "number" or it.k is not None:
                    problems.append(f"{it.id}: not an open number answer")
                if not in_grammar(it.answer_type, normalise_answer(it.answer)):
                    problems.append(f"{it.id}: answer {it.answer!r} not in grammar")
                if "Answer with a" not in it.question:
                    problems.append(f"{it.id}: no stated answer format")
                if json.loads(json.dumps(it.structured)) != it.structured:
                    problems.append(f"{it.id}: structured form is not JSON-stable")
                if "answer" in it.structured or "key" in it.structured:
                    problems.append(f"{it.id}: structured form carries the key")
    return problems
