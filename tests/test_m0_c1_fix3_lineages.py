# ruff: noqa: E501
"""C1 fix round 3: mechanical checks of every new lineage (``lineages_c1_fix3_*``). Self-checked only (not independent review, not Astra validation).

Per lineage and level: the build is deterministic; the program runs in a fresh restricted process twice and equals the key; the independent tree-walking second solver agrees; exactly one print;
the structured form carries no key and is JSON-stable; every identifier of the program is drawn (a differential test: renaming the drawn pool leaves the program unchanged up to renaming);
the retry rate is low (Retry is raised only for validity). The registry is separate from ``core.REGISTRY``."""

from __future__ import annotations

import json

import pytest

from studies.m0.c1_batch1_capacity import alpha_key
from studies.m0.c1grammar import render, run_isolated
from studies.m0.core import (
    ALL_LEVELS,
    REGISTRY,
    Item,
    Lineage,
    Retry,
    build_item,
    lineages_of,
    stream,
)
from studies.m0.lineages_c1_common import _count_prints, load_batch1
from studies.m0.lineages_c1_fix3 import FIX3, NOT_REGISTERED, SUPERSEDES3, VARIANT, load_fix3
from studies.m0.lineages_c1_rev2 import load_rev2
from studies.m0.scoring import in_grammar, normalise_answer
from studies.m0.solvers_c1 import c1_trace

LINEAGES = load_fix3()
IDS = [x.id for x in LINEAGES]


def items(lin: Lineage, level: int, n: int, label: str = "t") -> list[Item]:
    r = stream(953951, "c1-fix3-tests", label, lin.id, str(level))
    return [build_item(lin, level, r, "A", f"{lin.id}/{label}/{level}/{i}") for i in range(n)]


def test_registry_is_separate_and_ids_are_new() -> None:
    assert len(IDS) == len(set(IDS)) == 25
    old_ids = {x.id for x in [*lineages_of("C1"), *load_batch1(), *load_rev2()]}
    assert not set(IDS) & old_ids
    registered = {y.id for lins in REGISTRY.values() for y in lins}
    assert not set(IDS) & registered
    assert set(SUPERSEDES3) == set(IDS)
    assert all(v in old_ids for v in SUPERSEDES3.values())
    assert set(VARIANT) <= set(IDS)
    assert all(x.id.endswith("_f3") for x in FIX3)


def test_not_registered_are_documented_and_absent() -> None:
    for lid in ("C1.insertion_sort", "C1.minmax_track", "C1.kadane_scan"):
        assert lid in NOT_REGISTERED and len(NOT_REGISTERED[lid]) > 80
        assert lid not in IDS
    assert not any("kadane" in i or "insertion" in i or "minmax" in i for i in IDS)


@pytest.mark.parametrize("lid", IDS)
def test_lineage_mechanics(lid: str) -> None:
    lin = next(x for x in LINEAGES if x.id == lid)
    for lv in ALL_LEVELS:
        its = items(lin, lv, 12)
        again = build_item(lin, lv, stream(953951, "c1-fix3-tests", "t", lin.id, str(lv)), "A", "d")
        assert again.question == its[0].question, f"{lid} L{lv} not deterministic"
        srcs = [render(it.structured["program"]) for it in its]
        run1, run2 = run_isolated(srcs), run_isolated(srcs)
        for it, a, b in zip(its, run1, run2, strict=True):
            assert a["out"] == it.answer and b["out"] == it.answer, f"{it.id}: {a} {b} vs {it.answer!r}"
            assert c1_trace(it.structured) == it.answer, f"{it.id}: second solver"
            assert it.answer_type == "line" and it.k is None and in_grammar("line", normalise_answer(it.answer))
            assert set(it.structured) == {"program"} and json.loads(json.dumps(it.structured)) == it.structured
            assert _count_prints(it.structured["program"]) == 1
            assert normalise_answer(it.answer) == it.answer, "the answer must survive the scorer's normalisation unchanged"


@pytest.mark.parametrize("lid", IDS)
def test_every_identifier_is_drawn(lid: str) -> None:
    """Differential: build each item twice from one stream, once as written and once with every DRAWN name replaced by 'zz_' + name (a pool no fixed identifier can equal); the two programs
    must be the same up to renaming and have the same key. A fixed identifier equal to a drawn one would make them differ."""
    lin = next(x for x in LINEAGES if x.id == lid)
    g = lin.build.__globals__
    orig = g["names"]
    bad = []
    for lv in ALL_LEVELS:
        for t in range(6):
            a = build_item(lin, lv, stream(953952, "collide", lin.id, str(lv), str(t)), "A", "a")
            g["names"] = lambda r, k: ["zz_" + x for x in orig(r, k)]
            try:
                b = build_item(lin, lv, stream(953952, "collide", lin.id, str(lv), str(t)), "A", "b")
            finally:
                g["names"] = orig
            if alpha_key(render(a.structured["program"])) != alpha_key(render(b.structured["program"])) or a.answer != b.answer:
                bad.append((lv, t))
    assert not bad, bad


@pytest.mark.parametrize("lid", IDS)
def test_retries_are_rare(lid: str) -> None:
    """Retry is for validity only; a lineage that needs many redraws per item would be conditioning on something."""
    lin = next(x for x in LINEAGES if x.id == lid)
    for lv in (0, 3, 6):
        r = stream(953953, "retries", lin.id, str(lv))
        retries = built = 0
        while built < 60:
            try:
                lin.build(lv, r)
                built += 1
            except Retry:
                retries += 1
        assert retries / built < 12, (lid, lv, retries, built)
