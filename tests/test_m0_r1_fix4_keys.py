# ruff: noqa: E501
"""R1 fix round 4: the answer keys of the twelve surviving shapes (and the two dropped at the second stage) re-derived by the round-3 / revision-4 solvers that already exist in the test suite
(``test_m0_r1_fix3_keys.SOLVERS``, ``test_m0_r1_rev4_shapes.CHECKS``, ``solvers_r1``). A self-check, NOT the independent second solver that ruling R-9 requires and not the auditors' text-only solvers
(those were run in scratch; see NOTES_FIX4_R1.md)."""

from __future__ import annotations

import importlib.util
import random
import re
import sys
from pathlib import Path

import pytest

from studies.m0 import core
from studies.m0 import solvers_r1 as s1
from studies.m0.lineages_r1_fix4_clusters import candidates_v4

TESTS = Path(__file__).resolve().parent


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"fix4_keys_{name}", TESTS / f"{name}.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


K3 = _load("test_m0_r1_fix3_keys")
R4 = _load("test_m0_r1_rev4_shapes")


def _solver(lid: str):
    b = re.sub(r"_r\d+$", "", lid.split(".", 1)[1])
    if lid.endswith(("_r5", "_r6")) and b in K3.SOLVERS:
        return lambda it: K3.SOLVERS[b](it.structured)
    if f"{b}_r4" in R4.CHECKS:
        return R4.CHECKS[f"{b}_r4"]
    if lid in s1.SOLVERS:
        return lambda it: s1.SOLVERS[lid](it.structured)
    if b == "venn_counting":
        return R4.CHECKS["venn_counting_r4"]
    raise KeyError(lid)


@pytest.mark.parametrize("lin", candidates_v4(), ids=lambda x: x.id)
def test_the_existing_second_solver_agrees_with_the_key(lin) -> None:
    solve = _solver(lin.id)
    for lv in range(7):
        r = random.Random(9000 + lv)
        for i in range(40):
            it = core.build_item(lin, lv, r, "A", f"x{i}")
            assert solve(it) == it.answer, (lin.id, lv, it.question[:200])


def test_the_solver_detects_a_wrong_key_on_a_repaired_shape() -> None:
    lin = next(x for x in candidates_v4() if x.id == "R1.knights_knaves_r6")
    it = core.build_item(lin, 3, random.Random(1), "A", "x")
    wrong = "knave" if it.answer == "knight" else "knight"
    assert _solver(lin.id)(it) != wrong
