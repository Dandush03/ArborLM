# ruff: noqa: E501
"""R2 batch 1, family "dynprog": four dynamic-programming / scan procedures with different recurrences (strict reading: each is a
different general algorithm; they share only the paradigm, which the manifest log flags for the lead)."""

from __future__ import annotations

import random

from studies.m0.core import Built, Retry
from studies.m0.lineages_r2_common import batch1, lst, until


def lcs(a: str, b: str) -> int:
    prev = [0] * (len(b) + 1)
    for ca in a:
        cur = [0]
        for j, cb in enumerate(b, 1):
            cur.append(prev[j - 1] + 1 if ca == cb else max(prev[j], cur[j - 1]))
        prev = cur
    return prev[-1]


@batch1("dynprog")
def lcs_length(level: int, r: random.Random) -> Built:
    """Procedure: two-sequence prefix table (longest common subsequence). structured: {"a": str, "b": str}.
    Answer: the length of the longest string that is a subsequence (letters kept in order, not necessarily adjacent) of both strings."""
    alpha = "abcde"[: r.randint(2, 4) if level <= 1 else r.randint(2, 5)]

    def make() -> tuple[str, str]:
        return ("".join(r.choice(alpha) for _ in range(7 + level + r.randint(0, 4))), "".join(r.choice(alpha) for _ in range(7 + level + r.randint(0, 4))))

    def overlap(a: str, b: str) -> int:
        return sum(min(a.count(c), b.count(c)) for c in alpha)

    a, b = until(300, make, lambda ab: lcs(*ab) >= 3 and (overlap(*ab) != lcs(*ab) or r.random() < 0.3))
    ans = lcs(a, b)
    q = (f"A subsequence of a string is what is left after deleting zero or more of its letters, with the remaining letters kept in their original order (the letters need not be next to each other). "
         f"What is the length of the longest string that is a subsequence of both '{a}' and '{b}'?")
    return Built(q, {"a": a, "b": b}, str(ans), "number", None)


def coin_min(coins: list[int], amount: int) -> int | None:
    inf = 10**9
    best = [0] + [inf] * amount
    for v in range(1, amount + 1):
        for c in coins:
            if c <= v and best[v - c] + 1 < best[v]:
                best[v] = best[v - c] + 1
    return None if best[amount] >= inf else best[amount]


def coin_greedy(coins: list[int], amount: int) -> int | None:
    n, rest = 0, amount
    for c in sorted(coins, reverse=True):
        n += rest // c
        rest %= c
    return n if rest == 0 else None


@batch1("dynprog")
def coin_change_min(level: int, r: random.Random) -> Built:
    """Procedure: unbounded-supply capacity table (fewest coins). structured: {"coins": [int], "amount": int}.
    Answer: the fewest coins that sum exactly to amount (the amount is always reachable). In 80% of items (drawn per item) taking the largest coin first is NOT optimal; in 90% the amount divided by the largest coin, rounded up, is not the answer."""
    k = 3 if level < 3 else 4
    hard = r.random() < 0.8

    def make() -> tuple[list[int], int]:
        return sorted(r.sample(range(2, 10 + 3 * level), k)), r.randint(20 + 8 * level, 70 + 16 * level)

    def ok(ca: tuple[list[int], int]) -> bool:
        o = coin_min(*ca)
        return o is not None and (coin_greedy(*ca) != o) == hard and (-(-ca[1] // max(ca[0])) != o or r.random() < 0.1)

    coins, amount = until(500, make, ok)
    opt = coin_min(coins, amount)
    assert opt is not None
    q = (f"You have an unlimited supply of coins worth {lst(coins[:-1])} and {coins[-1]}. What is the smallest number of coins that add up to exactly {amount}?")
    return Built(q, {"coins": coins, "amount": amount}, str(opt), "number", None)


def lis(xs: list[int]) -> int:
    best = [1] * len(xs)
    for i in range(len(xs)):
        for j in range(i):
            if xs[j] < xs[i]:
                best[i] = max(best[i], best[j] + 1)
    return max(best)


@batch1("dynprog")
def lis_length(level: int, r: random.Random) -> Built:
    """Procedure: longest strictly increasing subsequence. structured: {"xs": [int]} (distinct). Answer: its length. In 70% of items "ascents + 1" and "longest run of ascents" are not the answer."""
    n = 9 + 2 * level + r.randint(0, 10)

    def asc(xs: list[int]) -> int:
        return 1 + sum(1 for i in range(1, len(xs)) if xs[i] > xs[i - 1])

    def run(xs: list[int]) -> int:
        best = cur = 1
        for i in range(1, len(xs)):
            cur = cur + 1 if xs[i] > xs[i - 1] else 1
            best = max(best, cur)
        return best

    xs = until(300, lambda: r.sample(range(1, 10 * n), n), lambda v: lis(v) >= 3 and (lis(v) != asc(v) or r.random() < 0.3) and (lis(v) != run(v) or r.random() < 0.3))
    ans = lis(xs)
    q = (f"Choose some of these numbers, keeping the order in which they are written, so that each chosen number is larger than the one chosen before it (the chosen numbers need not be next to each other). "
         f"What is the largest count of numbers you can choose? Numbers: {lst(xs)}.")
    return Built(q, {"xs": xs}, str(ans), "number", None)


def max_block(xs: list[int]) -> int:
    best, cur = xs[0], xs[0]
    for x in xs[1:]:
        cur = max(x, cur + x)
        best = max(best, cur)
    return best


@batch1("dynprog")
def max_subarray_sum(level: int, r: random.Random) -> Built:
    """Procedure: running best-ending-here scan (Kadane). structured: {"xs": [int]}. Answer: the largest sum of one or more neighbouring numbers
    (a block with no gaps). Items are rejected when the answer is the single largest number, the sum of the positives or the total."""
    n = 6 + 2 * level
    xs = [r.randint(-9, 9) for _ in range(n)]
    if sum(1 for x in xs if x < 0) < 2 or sum(1 for x in xs if x > 0) < 2:
        raise Retry
    ans = max_block(xs)
    if ans in (max(xs), sum(x for x in xs if x > 0), sum(xs)):
        raise Retry
    q = (f"Pick a block of one or more numbers that sit next to each other in this row (no gaps). What is the largest total a block can have? Row: {lst(xs)}.")
    return Built(q, {"xs": xs}, str(ans), "number", None)
