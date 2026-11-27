# ruff: noqa: E501
"""M1 fix round 3: the assertions of the new tests, written as functions that RETURN problems, so the same check can be applied to a NEW shape (the test passes when the list is empty) and to the
PRE-FIX shape (``m1_fix3_failing_first.py``: the list must be non-empty, which is the evidence that the test genuinely fails on the old code). Self-check only."""

from __future__ import annotations

import re
from collections import Counter
from fractions import Fraction
from typing import Any

from studies.m0.core import ALL_LEVELS, Lineage, Retry, build_item, stream
from studies.m0.m1_fix3_shortcuts import spec, stem_of


def _build(lin: Lineage, level: int, rng: Any) -> Any:
    """``lin.build`` with the core's own treatment of ``Retry`` (old shapes raise it; the new ones never do)."""
    for _ in range(500):
        try:
            return lin.build(level, rng)
        except Retry:
            continue
    raise RuntimeError("500 retries")


def retry_levels(lin: Lineage, n: int = 80, seed: int = 411001) -> list[int]:
    """Levels at which the builder itself raises ``Retry`` within n draws (a redraw exists inside the builder)."""
    bad = []
    for lv in ALL_LEVELS:
        rng = stream(seed, "no-retry", lin.id, str(lv))
        for _ in range(n):
            try:
                lin.build(lv, rng)
            except Retry:
                bad.append(lv)
                break
    return bad


def format_problems(lin: Lineage, n: int = 20, seed: int = 411002) -> list[str]:
    """Problems with the stated answer format: the item must END with the format sentence (whole number, or number with at most two decimals)."""
    out: list[str] = []
    for lv in ALL_LEVELS:
        rng = stream(seed, "fmt", lin.id, str(lv))
        for _ in range(n):
            q = _build(lin, lv, rng).question
            if not re.search(r"Answer with a (whole number|number; if it is not whole)[^.]*\.( |$)|Answer with a whole number \(write a minus sign if it is negative\)\.$", q):
                out.append(f"L{lv}: no stated answer format: {q[-90:]!r}")
                break
    return out


def shape_mix_problems(lin: Lineage, key: str, values: set[str], n: int = 1500, tol: float = 0.06, seed: int = 411003) -> list[str]:
    out = []
    for lv in ALL_LEVELS:
        rng = stream(seed, "mix", lin.id, str(lv))
        c = Counter(str(build_item(lin, lv, rng, "A", "t").structured.get(key)) for _ in range(n))
        if set(c) != values:
            out.append(f"L{lv}: values {sorted(c)} != {sorted(values)}")
            continue
        for v, k in sorted(c.items()):
            if abs(k / n - 1 / len(values)) >= tol:
                out.append(f"L{lv}: {v} has share {k / n:.2f}")
    return out


def rule_rate(lin: Lineage, rule: str, level: int, n: int = 1000, seed: int = 411004) -> float:
    """Share of items (over ALL n items; a rule that does not apply counts as a miss) on which the cheap rule ``rule`` of the shortcut battery gives the key."""
    rng = stream(seed, "rule", lin.id, str(level))
    hit = 0
    st = stem_of(lin.id)
    for _ in range(n):
        it = build_item(lin, level, rng, "A", "t")
        v = spec(st, it.structured).get(rule)
        hit += v is not None and v == Fraction(it.answer)
    return hit / n


def base_rate(lin: Lineage, level: int, n: int = 1500, seed: int = 411005) -> float:
    """The most frequent answer's share, fitted on one half and scored on the other (two folds)."""
    rng = stream(seed, "base", lin.id, str(level))
    ans = [build_item(lin, level, rng, "A", "t").answer for _ in range(n)]
    a, b = ans[0::2], ans[1::2]
    ma, mb = Counter(a).most_common(1)[0][0], Counter(b).most_common(1)[0][0]
    return (sum(x == ma for x in b) / len(b) + sum(x == mb for x in a) / len(a)) / 2


def digit_both_readings_problems(lin: Lineage, level: int = 2, n: int = 300, seed: int = 411006) -> list[str]:
    """Items of a digit puzzle whose answer is not unique under 'the digit d is in it at least once' AND 'it has exactly one digit d' read in turn (a clue 'contains_digit')."""
    from studies.m0.lineages_m1_fix3_c import clue_holds

    out: list[str] = []
    rng = stream(seed, "digit", lin.id, str(level))
    for _ in range(n):
        it = build_item(lin, level, rng, "A", "t")
        nd = it.structured["digits"]
        cl = [tuple(c) for c in it.structured["clues"]]
        for once in (False, True):
            cands = [m for m in range(10 ** (nd - 1), 10**nd) if all(clue_holds(m, tuple(int(ch) for ch in str(m)), c, once) for c in cl)]
            if cands != [int(it.answer)]:
                out.append(f"{'exactly once' if once else 'at least once'}: candidates {cands[:4]} for key {it.answer}")
                break
    return out


def grid_wording_problems(lin: Lineage, n: int = 40, seed: int = 411007) -> list[str]:
    """The old sentence 'the sides of squares that do not touch another square' has a second reading; the new item must define the perimeter as the sides that belong to exactly one square."""
    out: list[str] = []
    rng = stream(seed, "grid", lin.id)
    for _ in range(n):
        q = _build(lin, 3, rng).question
        if "do not touch another square" in q:
            out.append("the ambiguous phrase 'squares that do not touch another square' is present")
            break
        if "belong to exactly one square" not in q:
            out.append("the perimeter is not defined as the unit sides that belong to exactly one square")
            break
    return out


def structured_problems(lin: Lineage, n: int = 20, seed: int = 411008) -> list[str]:
    import json

    out: list[str] = []
    for lv in ALL_LEVELS:
        rng = stream(seed, "struct", lin.id, str(lv))
        for _ in range(n):
            b = _build(lin, lv, rng)
            if json.loads(json.dumps(b.structured)) != b.structured:
                out.append(f"L{lv}: structured form not JSON-stable")
            if "answer" in b.structured or "key" in b.structured:
                out.append(f"L{lv}: structured form carries the key")
            if b.answer_type != "number" or b.k is not None:
                out.append(f"L{lv}: not an open number answer")
    return out[:3]


def any_item(lin: Lineage, level: int, seed: int = 411009) -> Any:
    return build_item(lin, level, stream(seed, "any", lin.id, str(level)), "A", "t")
