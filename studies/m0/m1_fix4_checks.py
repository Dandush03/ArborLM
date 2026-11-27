# ruff: noqa: E501
"""M1 fix round 4: checks as functions that RETURN problems (the tests pass when the list is empty). Self-check only: not independent review, not Astra, not human approval."""

from __future__ import annotations

from typing import Any

from studies.m0.core import ALL_LEVELS, Lineage, build_item, stream
from studies.m0.lineages_m1_fix4 import (
    ZERO_SENTENCE,
    level_parameter_values,
    stem,
    zero_rule_stated,
)
from studies.m0.m1_fix4_verify import verify


def identical_level_pairs(lin: Lineage, n: int = 300, seed: int = 13) -> list[str]:
    """Pairs of levels (a, b), a < b, whose items are byte-identical when built from the SAME random stream (the level is ignored between them): the audit-4 no-op test, over ALL 21 pairs."""
    out: list[str] = []
    for a in ALL_LEVELS:
        for b in ALL_LEVELS:
            if b <= a:
                continue
            ra, rb = stream(seed, "noop", lin.id), stream(seed, "noop", lin.id)
            same = 0
            for _ in range(n):
                x = build_item(lin, a, ra, "A", "x")
                y = build_item(lin, b, rb, "A", "x")
                same += (x.question, x.answer) == (y.question, y.answer)
            if same == n:
                out.append(f"{a}={b}")
    return out


def rising_parameter_problems(st: str) -> list[str]:
    v = level_parameter_values(st)
    return [f"level {i} -> {i + 1}: {v[i]} -> {v[i + 1]} is not rising" for i in range(6) if not v[i + 1] > v[i]]


def level_profile(lin: Lineage, n: int = 300, seed: int = 13) -> dict[str, list[float]]:
    """Per level: mean count of numbers printed and mean log10(|answer| + 1) (MEASURED)."""
    import math
    import re

    nums, logs = [], []
    for lv in ALL_LEVELS:
        r = stream(seed, "profile", lin.id, str(lv))
        its = [build_item(lin, lv, r, "A", "p") for _ in range(n)]
        nums.append(round(sum(len(re.findall(r"(?<![\w.])\d+(?:\.\d+)?", i.question.replace("$", " "))) for i in its) / n, 2))
        logs.append(round(sum(math.log10(abs(float(i.answer)) + 1) for i in its) / n, 3))
    return {"numbers": nums, "log10_answer": logs}


def key_problems(lin: Lineage, n: int = 200, seed: int = 4401) -> list[str]:
    """The answer key against the implementer's existing second derivation (``m1_fix4_verify``) from the structured form, all levels."""
    out: list[str] = []
    st = stem(lin.id)
    for lv in ALL_LEVELS:
        r = stream(seed, "keys", lin.id, str(lv))
        for i in range(n):
            it = build_item(lin, lv, r, "A", "k")
            try:
                got = verify(st, it.structured)
            except ValueError as e:
                out.append(f"L{lv} item {i}: {e}")
                break
            if got != it.answer:
                out.append(f"L{lv} item {i}: key {it.answer} != second derivation {got}")
                break
    return out


def slot_zero_problems(lin: Lineage, n: int = 400, seed: int = 4402) -> list[str]:
    """(b) the leading-zero convention: stated in EVERY item where 0 is allowed and the first-digit rule is not 'may not be 0'; not stated otherwise; and the key counts codes that start with 0 whenever the first-digit rule
    accepts 0 (checked by enumeration on the small items)."""
    import itertools

    from studies.m0.lineages_m1_fix3_b import _RULES_FIRST, _RULES_LAST

    out: list[str] = []
    seen_even_with_zero = 0
    for lv in ALL_LEVELS:
        r = stream(seed, "zero", lin.id, str(lv))
        for _ in range(n):
            it = build_item(lin, lv, r, "A", "z")
            s: dict[str, Any] = it.structured
            need = zero_rule_stated(s["digits"], s["first"])
            has = ZERO_SENTENCE in it.question
            if need != has:
                out.append(f"L{lv}: zero sentence {'missing' if need else 'present'} for digits {s['digits']} first={s['first']}")
                break
            if s["first"] in ("even", "lt5") and 0 in s["digits"] and len(s["digits"]) ** s["length"] <= 5000:
                gen = itertools.product(s["digits"], repeat=s["length"]) if s["repeat"] else itertools.permutations(s["digits"], s["length"])
                codes = [c for c in gen if _RULES_FIRST[s["first"]](c[0]) and _RULES_LAST[s["last"]](c[-1])]
                if len(codes) != int(it.answer):
                    out.append(f"L{lv}: enumeration {len(codes)} != key {it.answer}")
                    break
                seen_even_with_zero += any(c[0] == 0 for c in codes)
    if seen_even_with_zero == 0:
        out.append("no checked item had a code starting with 0 under an even / less-than-5 first-digit rule")
    return out
