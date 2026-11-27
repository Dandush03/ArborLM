# ruff: noqa: E501
"""R2 fix round 4: the six repaired shapes (``lineages_r2_fix4``) against second solvers written here from the structured form only (no generator code is called to solve), their determinism, that level 0 draws are
those of the fix-round-3 shapes (except the count_divisible wording), the wording clause of count_divisible, and the level-distinctness gate (``r2_fix4_levels``). Self-checks, not independent review."""

from __future__ import annotations

import json
import random
import re
from typing import Any

import pytest

from studies.m0.core import ALL_LEVELS, build_item
from studies.m0.r2_fix3_set import fix3_set
from studies.m0.r2_fix4_set import fix4_set

SET = fix4_set()
OLD = fix3_set()
NAMES = ("caesar_shift", "cheapest_network", "count_divisible", "crt_smallest", "expression_eval", "interval_scheduling")


def _items(name: str, lv: int, n: int, tag: str = "keys") -> list[Any]:
    r = random.Random(f"fix4-test-{tag}|{name}|{lv}")
    return [build_item(SET["R2." + name], lv, r, "A", "t") for _ in range(n)]


# ---------------------------------------------------------------- second solvers (structured form only)


def _caesar(s: dict[str, Any]) -> str:
    return "".join(" " if c == " " else chr((ord(c) - 97 + s["k"]) % 26 + 97) for c in s["text"])


def _prim(s: dict[str, Any]) -> int:
    adj: dict[str, list[tuple[int, str]]] = {}
    for a, b, w in s["cables"]:
        adj.setdefault(a, []).append((w, b))
        adj.setdefault(b, []).append((w, a))
    start = s["towns"][0]
    seen = {start}
    total = 0
    while len(seen) < len(s["towns"]):
        w, b = min((w, b) for a in sorted(seen) for w, b in adj[a] if b not in seen)
        seen.add(b)
        total += w
    return total


def _rounds(s: dict[str, Any]) -> str:
    iv = [(i + 1, a, b) for i, (a, b) in enumerate(s["meetings"])]
    chosen: list[tuple[int, int, int]] = []
    while True:
        ok = [m for m in iv if m not in chosen and all(m[2] <= c[1] or c[2] <= m[1] for c in chosen)]
        if not ok:
            break
        chosen.append(min(ok, key=lambda m: (m[2], m[0])))
    return ", ".join(str(m[0]) for m in sorted(chosen))


def _crt(s: dict[str, Any]) -> int:
    x = 1
    while not all(x % m == c for c, m in s["congruences"]):
        x += 1
    return x


def _expr(s: dict[str, Any]) -> int:
    text = s["text"]
    assert re.fullmatch(r"[0-9+\-*() ]+", text)
    if s["convention"] == "ranked":
        return int(eval(text))  # noqa: S307  (digits and + - * ( ) only, checked above; Python's precedence is the stated one)
    toks = re.findall(r"\d+|[-+*()]", text)
    pos = 0

    def expr() -> int:
        nonlocal pos
        v = atom()
        while pos < len(toks) and toks[pos] in "+-*":
            op = toks[pos]
            pos += 1
            w = atom()
            v = v + w if op == "+" else v - w if op == "-" else v * w
        return v

    def atom() -> int:
        nonlocal pos
        t = toks[pos]
        pos += 1
        if t == "(":
            v = expr()
            pos += 1
            return v
        return int(t)

    out = expr()
    assert pos == len(toks)
    return out


def _sum_div(s: dict[str, Any]) -> int:
    return sum(x for x in s["xs"] if x % s["m"] == 0 and x > s["t"])


SOLVERS: dict[str, Any] = {
    "caesar_shift": lambda s: _caesar(s),
    "cheapest_network": lambda s: str(_prim(s)),
    "interval_scheduling": _rounds,
    "crt_smallest": lambda s: str(_crt(s)),
    "expression_eval": lambda s: str(_expr(s)),
    "count_divisible": lambda s: str(_sum_div(s)),
}


@pytest.mark.parametrize("name", NAMES)
def test_key_matches_second_solver_at_every_level(name: str) -> None:
    for lv in ALL_LEVELS:
        for it in _items(name, lv, 40):
            assert SOLVERS[name](it.structured) == it.answer, (name, lv, it.question[:200])


@pytest.mark.parametrize("name", NAMES)
def test_determinism_and_json_stability(name: str) -> None:
    for lv in (0, 3, 6):
        a, b = _items(name, lv, 10, "det"), _items(name, lv, 10, "det")
        assert [x.question for x in a] == [x.question for x in b]
        for it in a:
            assert json.loads(json.dumps(it.structured)) == it.structured


@pytest.mark.parametrize("name", NAMES)
def test_registered_as_fix4_with_the_same_id_and_nothing_in_core(name: str) -> None:
    from studies.m0.core import REGISTRY
    from studies.m0.lineages_r2_fix4 import FIX4, SUPERSEDES

    assert f"R2.{name}" in {x.id for x in FIX4}
    assert SUPERSEDES[f"R2.{name}"] == f"R2.{name}"
    assert SET["R2." + name] is not OLD["R2." + name]
    assert all(x.build is not SET["R2." + name].build for v in REGISTRY.values() for x in v)  # core.REGISTRY does not hold the fix-4 builder


@pytest.mark.parametrize("name", ("caesar_shift", "cheapest_network", "crt_smallest", "expression_eval", "interval_scheduling"))
def test_level_zero_draws_are_those_of_the_fix3_shape(name: str) -> None:
    for seed in range(5):
        a = build_item(SET["R2." + name], 0, random.Random(f"fix4-l0|{name}|{seed}"), "A", "x")
        b = build_item(OLD["R2." + name], 0, random.Random(f"fix4-l0|{name}|{seed}"), "A", "x")
        assert (a.question, a.answer) == (b.question, b.answer)


def test_count_divisible_has_the_same_draws_and_a_repeats_clause() -> None:
    for lv in ALL_LEVELS:
        for seed in range(5):
            a = build_item(SET["R2.count_divisible"], lv, random.Random(f"fix4-cd|{lv}|{seed}"), "A", "x")
            b = build_item(OLD["R2.count_divisible"], lv, random.Random(f"fix4-cd|{lv}|{seed}"), "A", "x")
            assert a.structured == b.structured and a.answer == b.answer
            assert "Every entry of the list counts each time it appears" in a.question
            assert "Every entry" not in b.question


def test_count_divisible_keeps_repeats_in_the_key() -> None:
    # the set-of-values reading (audit 4, a4_wording) differs from the stated reading on a share of items; the key is the stated one
    differing = 0
    for lv in ALL_LEVELS:
        for it in _items("count_divisible", lv, 100, "rep"):
            s = it.structured
            alt = sum(x for x in sorted(set(s["xs"])) if x % s["m"] == 0 and x > s["t"])
            differing += str(alt) != it.answer
    assert differing > 50


@pytest.mark.parametrize("name", ("caesar_shift", "cheapest_network", "crt_smallest", "expression_eval", "interval_scheduling"))
def test_levels_are_distinct_with_a_rising_parameter(name: str) -> None:
    from studies.m0.r2_fix4_levels import KS_MIN, PARAM, check

    res = check(name, SET["R2." + name], n=120)
    assert name in PARAM
    # 120 items per level in the test (the recorded run uses 300): the same gate
    assert all(p["param_rises"] for p in res["pairs"]), res["parameter_mean_by_level"]
    assert all(p["best_ks"] >= KS_MIN for p in res["pairs"]), res["pairs"]


@pytest.mark.parametrize("name", ("caesar_shift", "cheapest_network", "interval_scheduling", "expression_eval"))
def test_the_fix3_shape_was_collapsed_in_pairs(name: str) -> None:
    """Failing-first evidence: the same gate on the shape held before this round reports a collapsed pair."""
    from studies.m0.r2_fix4_levels import check

    res = check(name, OLD["R2." + name], n=120)
    assert not res["levels_distinct"], res["pairs"]


def test_level_parameters_are_the_stated_ones() -> None:
    for lv in ALL_LEVELS:
        assert len(_items("caesar_shift", lv, 1)[0].structured["text"].split(" ")) == 1 + lv
        assert len(_items("cheapest_network", lv, 1)[0].structured["towns"]) == 8 + lv
        assert len(_items("count_divisible", lv, 1)[0].structured["xs"]) == 18 + 4 * lv
        for it in _items("crt_smallest", lv, 20):
            assert all(3 + 5 * lv <= m < 30 + 10 * lv for _c, m in it.structured["congruences"])
        for it in _items("interval_scheduling", lv, 5):
            assert max(a for a, _b in it.structured["meetings"]) // 24 == 4 + lv  # 5 + lv blocks, 24 minutes apart
