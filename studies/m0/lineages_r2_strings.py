# ruff: noqa: E501
"""R2 batch 1, family "strings": longest palindromic substring (grow around every centre)."""

from __future__ import annotations

import random

from studies.m0.core import Built, Retry
from studies.m0.lineages_r2_common import batch1


def longest_pal(s: str) -> int:
    best = 1
    for c in range(len(s)):
        for lo, hi in ((c, c), (c, c + 1)):
            while lo >= 0 and hi < len(s) and s[lo] == s[hi]:
                lo -= 1
                hi += 1
            best = max(best, hi - lo - 1)
    return best


@batch1("strings")
def longest_palindromic_substring(level: int, r: random.Random) -> Built:
    """Procedure: expand around each centre. structured: {"s": str}. Answer: the length of the longest block of neighbouring letters that reads the same forwards and backwards.
    A palindrome of a random length is planted in a random string, so the answer is spread; the true longest is computed afterwards (it may exceed the planted one)."""
    alpha = "abc" if level <= 2 else "abcd"
    n = 14 + 2 * level
    s = "".join(r.choice(alpha) for _ in range(n))
    plant = r.randint(3, 7 + level)
    half = "".join(r.choice(alpha) for _ in range(plant // 2))
    pal = half + (r.choice(alpha) if plant % 2 else "") + half[::-1]
    at = r.randint(0, n - plant)
    s = s[:at] + pal + s[at + plant :]
    ans = longest_pal(s)
    if ans < 3:
        raise Retry
    q = f"Look at the string '{s}'. Find the longest block of letters, all next to each other in the string, that reads the same forwards and backwards. How many letters long is it?"
    return Built(q, {"s": s}, str(ans), "number", None)
