# ruff: noqa: E501
"""P10IS1 quiet-rule arithmetic (ADR-0024 addendum, A3.1 items 1, 5 and 6). Pure functions, no clock, no machine. Every load is an INTEGER in hundredths: v = round(x, 2) x 100. Every difference, comparison,
percentile and limit is computed on those integers (floating point fails at the boundaries: 0.54 - 0.29 is 0.25000000000000006).

* nearest-rank percentile: the value at 1-indexed rank ceil(pct x n / 100) of the ascending values, in integer arithmetic (rank 114 of 120 and rank 342 of 360 for the 95th);
* median of an even number of values: the mean of the two middle values, compared exactly as TWICE the median (``median2``);
* the settled test (two-sided): thirds T1, T3 of the window in order; |2 med(T1) - 2 med(T3)| <= 2 x median_max and |P95(T1) - P95(T3)| <= p95_max;
* L = P95(window) + margin; L above the ceiling is refused, never clamped.
"""

import math
from collections.abc import Mapping, Sequence
from typing import Any


def hundredths(x: float) -> int:
    """v = round(x, 2) x 100 as an integer. ``round`` is correctly rounded (half to even on an exact tie), the product is within 1e-9 of an integer, so ``round`` of it is exact."""
    if not math.isfinite(x):
        raise ValueError("a load average is finite")
    return int(round(round(x, 2) * 100))


def nearest_rank(values: Sequence[int], pct: int) -> int:
    """The nearest-rank percentile of integers: the value at 1-indexed rank ceil(pct x n / 100) of the ascending values (integer arithmetic)."""
    n = len(values)
    if n == 0 or not 0 < pct <= 100:
        raise ValueError("a percentile needs values and 0 < pct <= 100")
    rank = (pct * n + 99) // 100
    return sorted(values)[rank - 1]


def median2(values: Sequence[int]) -> int:
    """TWICE the median, exactly: 2 x the middle value (odd n) or the sum of the two middle values (even n)."""
    n = len(values)
    if n == 0:
        raise ValueError("a median needs values")
    s = sorted(values)
    return 2 * s[n // 2] if n % 2 else s[n // 2 - 1] + s[n // 2]


def thirds(values: Sequence[int]) -> tuple[list[int], list[int], list[int]]:
    """The window in order, split into thirds of equal length (the window length is a multiple of three)."""
    n = len(values)
    if n == 0 or n % 3:
        raise ValueError("the window is split into three equal thirds")
    k = n // 3
    return list(values[:k]), list(values[k : 2 * k]), list(values[2 * k :])


def settled(window: Sequence[int], *, median_diff_max: int, p95_diff_max: int, percentile: int = 95) -> dict[str, Any]:
    """The two-sided settled test of A3.1 item 5 on the window loads (hundredths). Returns every figure."""
    t1, _, t3 = thirds(window)
    m1, m3 = median2(t1), median2(t3)
    p1, p3 = nearest_rank(t1, percentile), nearest_rank(t3, percentile)
    med_ok = abs(m1 - m3) <= 2 * median_diff_max  # |2 med(T1) - 2 med(T3)| <= 2 x 25 = 50
    p95_ok = abs(p1 - p3) <= p95_diff_max
    return {"median2_t1": m1, "median2_t3": m3, "median2_difference": m1 - m3, "median_ok": med_ok, "p95_t1": p1, "p95_t3": p3, "p95_difference": p1 - p3, "p95_ok": p95_ok, "settled": med_ok and p95_ok}


def derive(window: Sequence[int], q: Mapping[str, Any]) -> dict[str, Any]:
    """P95 (nearest rank), L = P95 + margin and the settled test for a window of loads in hundredths, with the config's figures; ``above_ceiling`` is L > ceiling (the window is then refused, L is never clamped)."""
    if len(window) != int(q["baseline_samples"]):
        raise ValueError(f"the window has {int(q['baseline_samples'])} samples, not {len(window)}")
    p95 = nearest_rank(window, int(q["percentile"]))
    limit = p95 + int(q["load_margin"])
    st = settled(window, median_diff_max=int(q["settled_median_diff_max"]), p95_diff_max=int(q["settled_p95_diff_max"]), percentile=int(q["percentile"]))
    return {"load_p95": p95, "load_limit": limit, "above_ceiling": limit > int(q["load_ceiling"]), "report_above": limit > int(q["load_report_above"]), "settled": st}
