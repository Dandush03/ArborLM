# ruff: noqa: E501
"""R2 batch 1, family "search": the trace of binary search (halving) with its midpoint convention stated."""

from __future__ import annotations

import random

from studies.m0.core import Built, Retry
from studies.m0.lineages_r2_common import batch1, lst


def probes(xs: list[int], target: int) -> list[int]:
    """values looked at, in order, with low=1, high=n, middle = floor((low+high)/2) (1-based)."""
    lo, hi = 1, len(xs)
    seen = []
    while lo <= hi:
        mid = (lo + hi) // 2
        seen.append(xs[mid - 1])
        if xs[mid - 1] == target:
            break
        if target < xs[mid - 1]:
            hi = mid - 1
        else:
            lo = mid + 1
    return seen


@batch1("search")
def binary_search_trace(level: int, r: random.Random) -> Built:
    """Procedure: binary search with middle = floor((low+high)/2). structured: {"xs": [int] (ascending, distinct), "target": int, "ask": "values" | "third"}.
    Positions are 1..n; low=1, high=n; look at the middle; stop if it equals the target; if the target is smaller set high = middle - 1, else low = middle + 1; stop (not found) when low > high.
    Answer: the values looked at in order (comma list), or the third value looked at. The target is in the list about 70% of the time. Rejected: fewer than 3 values looked at."""
    n = 8 + 3 * level + r.randint(0, 2)
    xs = sorted(r.sample(range(1, 4 * n), n))
    present = r.random() < 0.7
    target = r.choice(xs) if present else r.choice([v for v in range(1, 4 * n) if v not in xs])
    seen = probes(xs, target)
    if len(seen) < 3:
        raise Retry
    third = r.random() >= 0.6
    if third and seen[2] == target and r.random() < 0.8:
        raise Retry  # the third look is rarely the target itself, so the question text does not give the answer away
    head = (f"A sorted list of {n} numbers (smallest first) is searched for {target}. The positions are numbered 1 to {n}. The search keeps a lower position (first 1) and an upper position (first {n}). "
            "Each round it looks at the number in the position halfway between them, rounded down when needed (the sum of the two positions divided by 2, rounded down). If that number is the target the search stops; "
            "if the target is smaller, the upper position becomes one less than the position just looked at; otherwise the lower position becomes one more. If the lower position ever exceeds the upper position the search stops, having found nothing. "
            f"The list: {lst(xs)}. ")
    if not third:
        return Built(head + "Which numbers does the search look at, in order? Give them separated by commas.", {"xs": xs, "target": target, "ask": "values"}, lst(seen), "list", None)
    return Built(head + "Which is the third number the search looks at?", {"xs": xs, "target": target, "ask": "third"}, str(seen[2]), "number", None)
