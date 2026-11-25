# ruff: noqa: E501
"""Shared pieces of the C1 batch-1 lineages (lineage repair, C1 batch 1).

The batch lineages are kept in their OWN registry (``BATCH1``), not in ``core.REGISTRY``: they have no registered second-solver entry
yet, and the existing suite parametrises over the core registry. Ids are ``C1.<function name>`` so that registration later changes
nothing in the ids a solver agent sees.

What a lineage is here (STRICT reading, lead ruling): the general ALGORITHM that the generated program implements. Constants, data,
variable names, comparison direction, which value is printed at the end and the size of the input are shapes of one lineage, not new
lineages. Each lineage's docstring states its procedure in one line.

The structured form, the gold key and the checker are those of the existing C1 lineages: ``{"program": <tree of c1grammar>}``, the key is
what the locked interpreter prints, and the independent second solver is the tree walker ``solvers_c1.c1_trace`` (all programs here use
only the node kinds it supports; no ``aug`` on lists, no ``sorted``/``range`` calls, no string methods beyond upper/lower/replace/count).
"""

from __future__ import annotations

import importlib
import random
from collections.abc import Callable
from typing import Any

from studies.m0.core import ALL_LEVELS, Built, Lineage, build_item, lineages_of, stream
from studies.m0.lineages_c1 import (  # reused: same question frame, same retry rule, same variable pool
    LETTERS,
    VARS,
    _finish,
    _names,
)

__all__ = ["B", "BATCH1", "C", "FAMILY_MODULES", "N", "S", "V", "Builder", "LETTERS", "VARS", "batch", "check_family", "finish", "load_batch1", "names"]

BATCH1: list[Lineage] = []
FAMILY_MODULES = ("while", "lists", "swaps", "minmax", "strings", "functions", "stacks", "tables", "graphs", "simulation", "references")
Builder = Callable[[int, random.Random], Built]


def N(v: int) -> list:
    return ["n", v]


def S(v: str) -> list:
    return ["s", v]


def V(v: str) -> list:
    return ["v", v]


def B(op: str, a: list, b: list) -> list:
    return ["b", op, a, b]


def C(op: str, a: list, b: list) -> list:
    return ["c", op, a, b]


def AND(a: list, b: list) -> list:
    return ["and", a, b]


def OR(a: list, b: list) -> list:
    return ["or", a, b]


def IDX(a: list, i: list) -> list:
    return ["idx", a, i]


def CALL(f: str, *args: list) -> list:
    return ["call", f, *args]


def LIST(vals: list[int]) -> list:
    return ["list", *[N(v) for v in vals]]


def finish(prog: list[list]) -> Built:
    return _finish(prog)


def names(r: random.Random, k: int) -> list[str]:
    return _names(r, k)


def batch(family: str) -> Callable[[Builder], Builder]:
    def deco(fn: Builder) -> Builder:
        lid = f"C1.{fn.__name__}"
        if any(x.id == lid for x in BATCH1) or any(x.id == lid for x in lineages_of("C1")):
            raise ValueError(f"duplicate lineage id {lid}")
        if family not in FAMILY_MODULES:
            raise ValueError(f"unknown family {family}")
        BATCH1.append(Lineage(lid, "C1", family, fn))
        return fn

    return deco


def load_batch1() -> list[Lineage]:
    for fam in FAMILY_MODULES:
        importlib.import_module(f"studies.m0.lineages_c1_{fam}")
    return sorted(BATCH1, key=lambda x: x.id)


def check_family(family: str, per_level: int = 40) -> list[str]:
    """Mechanical checks on every batch lineage of one family; returns the problems (empty when none).

    For each lineage and each of the seven levels: ``per_level`` items are built; the generation is deterministic; the questions are
    mostly distinct; the key is in the line grammar; the program is run TWICE in fresh restricted processes (``run_isolated``) and both runs
    equal the key; the existing tree-walking second solver ``solvers_c1.c1_trace`` agrees on every item; the structured form is JSON-stable
    and carries no key; the program contains exactly one print and no node kind the second solver lacks.
    """
    import json

    from studies.m0.c1grammar import run_isolated
    from studies.m0.scoring import in_grammar, normalise_answer
    from studies.m0.solvers_c1 import c1_trace

    problems: list[str] = []
    lins = [x for x in load_batch1() if x.family == family]
    if not lins:
        return [f"no batch lineage in family {family}"]
    for lin in lins:
        for lv in ALL_LEVELS:
            r = stream(953702, "c1-family-check", lin.id, str(lv))
            items = [build_item(lin, lv, r, "A", f"{lin.id}/{lv}/{i}") for i in range(per_level)]
            again = build_item(lin, lv, stream(953702, "c1-family-check", lin.id, str(lv)), "A", "d")
            if again.question != items[0].question:
                problems.append(f"{lin.id} L{lv}: not deterministic")
            if len({it.question for it in items}) < 0.9 * per_level:
                problems.append(f"{lin.id} L{lv}: fewer than 90% distinct questions")
            from studies.m0.c1grammar import render

            srcs = [render(it.structured["program"]) for it in items]
            run1, run2 = run_isolated(srcs), run_isolated(srcs)
            for it, a, b in zip(items, run1, run2, strict=True):
                if a["out"] != it.answer or b["out"] != it.answer:
                    problems.append(f"{it.id}: isolated runs {a}/{b} differ from key {it.answer!r}")
                if c1_trace(it.structured) != it.answer:
                    problems.append(f"{it.id}: second solver disagrees")
                if not in_grammar(it.answer_type, normalise_answer(it.answer)) or it.answer_type != "line" or it.k is not None:
                    problems.append(f"{it.id}: answer {it.answer!r} / type {it.answer_type} / k {it.k} not as C1 defines")
                if json.loads(json.dumps(it.structured)) != it.structured:
                    problems.append(f"{it.id}: structured form is not JSON-stable")
                if set(it.structured) != {"program"}:
                    problems.append(f"{it.id}: structured form has keys {sorted(it.structured)}")
                if _count_prints(it.structured["program"]) != 1:
                    problems.append(f"{it.id}: not exactly one print statement")
    return problems


def _count_prints(prog: list[Any]) -> int:
    n = 0
    for st in prog:
        if st[0] == "print":
            n += 1
        elif st[0] in ("for",):
            n += _count_prints(st[5])
        elif st[0] == "while":
            n += _count_prints(st[2])
        elif st[0] == "if":
            n += _count_prints(st[2]) + _count_prints(st[3])
        elif st[0] == "def":
            n += _count_prints(st[3])
    return n
