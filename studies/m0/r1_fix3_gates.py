# ruff: noqa: E501
# mypy: disable-error-code="type-arg,no-untyped-call,no-any-return,arg-type,assignment,index,call-overload,var-annotated,list-item,unused-ignore,no-untyped-def"
"""The R1 shortcut gate with the three small issues of the third audit fixed (AUDIT3_R1.md section 5), in a NEW module; ``lineages_r1_shortcuts`` is unchanged.

1. ``numbers``: 'one of the 2 options shown' (minimax) counted the 2 as data; 'option' and 'options' are now structure nouns.
2. ``generic``: an item whose question has no '?' (categories_follow: 'Consider the statement: ...') got no yes / no heuristic at all; the statement sentence is now read as the question.
3. ``stated_reading``: 'No X are Y' and 'Some X are Y' are symmetric, so a stated premise in the reverse order says the same; it returned None. 'All X are Y' still says something only in the same order.

Measured, not thresholded: as in the earlier gate. ``run_battery`` is the earlier function with these three readings.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Sequence
from typing import Any

from studies.m0 import lineages_r1_shortcuts as old
from studies.m0.core import Item, Lineage

Pred = old.Pred
_STRUCTURE_NOUNS = (*old._STRUCTURE_NOUNS, "option", "options")


def numbers(body: str) -> list[int]:
    """As the earlier ``numbers`` (signed, without counts of structure), with 'option(s)' a structure noun."""
    out = []
    for m in old._NUM.finditer(body):
        if m.group(1) and m.group(1).lower() in _STRUCTURE_NOUNS:
            continue
        out.append(int(re.match(r"-?\d+", m.group(0)).group(0)))  # type: ignore[union-attr]
    return out


def stated_reading(q1: str, sentence: str, ents: list[str]) -> str | None:
    """As the earlier ``_stated_reading`` except that "No ..." and "Some ..." premises are symmetric (the order of the two names does not matter)."""
    if re.match(r"\s*(No|Some)\b", sentence):
        return "no" if any(w.lower() in old._NEG for w in old._WORD.findall(sentence)) else "yes"
    return old._stated_reading(q1, sentence, ents)


def split_body(q: str) -> tuple[str, str]:
    """As the earlier ``split_body``, and for a question without '?' the sentence that says 'Consider the statement' (and everything after it) is the question."""
    if "?" not in q:
        m = re.search(r"Consider the statement", q)
        if m:
            return q[: m.start()].rstrip(), q[m.start() :]
    return old.split_body(q)


def generic(it: Item) -> dict[str, Pred]:
    """The earlier generic battery with the three fixes. For a yes / no item the asked entities are those of the statement sentence."""
    body, tail = split_body(it.question)
    out: dict[str, Pred] = {}
    base = old.generic(it)
    out.update({k: v for k, v in base.items() if k not in ("largest_number", "smallest_number", "last_number", "asked_pair_stated_verbatim", "asked_entity_never_mentioned")})
    if it.answer_type in ("yn", "ynu"):
        q1 = next((s for s in re.split(r"(?<=[.?!])\s+", tail) if "?" in s or "Consider the statement" in s), tail)
        ents = list(dict.fromkeys(w for w in old.words(q1) if w in old._ENT))[:2]
        if len(ents) == 2:
            hit = [s for s in re.split(r"(?<=[.?!])\s+", body) if ents[0] in s and ents[1] in s]
            out["asked_pair_stated_verbatim"] = stated_reading(q1, hit[0], ents) if hit else None
            out["asked_entity_never_mentioned"] = ("cannot be determined" if it.answer_type == "ynu" else "no") if any(e not in body for e in ents) else None
    if it.answer_type == "number":
        nums = numbers(body)
        if nums:
            out["largest_number"] = str(max(nums))
            out["smallest_number"] = str(min(nums))
            out["last_number"] = str(nums[-1])
    return out


def run_battery(lin: Lineage, items: Sequence[Item]) -> dict[str, Any]:
    """The earlier ``run_battery`` (same scoring, same two-sided per-level rows) with this module's ``generic``."""
    saved = old.generic
    try:
        old.generic = generic  # type: ignore[assignment]
        return old.run_battery(lin, items)
    finally:
        old.generic = saved  # type: ignore[assignment]


def max_departure_by_level(result: dict[str, Any]) -> dict[str, tuple[str, float]]:
    """Per level: the heuristic with the largest absolute departure from chance and the value (accuracy - chance; the anti reading for closed answers)."""
    best: dict[str, tuple[str, float]] = {}
    for h in result["heuristics"]:
        for lv, row in h["per_level"].items():
            for v in (row["departure"], row["anti_departure"]):
                if v is not None and abs(v) > abs(best.get(lv, ("", 0.0))[1]):
                    best[lv] = (h["heuristic"], v)
    return best


__all__ = ["numbers", "stated_reading", "split_body", "generic", "run_battery", "max_departure_by_level", "Counter"]
