# ruff: noqa: E501
"""R2 batch 1, family "greedy": two exchange-argument / priority-queue procedures (earliest-finish selection; repeated merge of the two smallest)."""

from __future__ import annotations

import heapq
import random

from studies.m0.core import Built, Retry
from studies.m0.lineages_r2_common import batch1, lst, until


def max_compatible(iv: list[list[int]]) -> int:
    """most pairwise non-overlapping intervals (touching ends do not overlap): earliest finish first."""
    n, last = 0, -(10**9)
    for s, e in sorted(iv, key=lambda x: (x[1], x[0])):
        if s >= last:
            n += 1
            last = e
    return n


def earliest_start_greedy(iv: list[list[int]]) -> int:
    n, last = 0, -(10**9)
    for s, e in sorted(iv, key=lambda x: (x[0], x[1])):
        if s >= last:
            n += 1
            last = e
    return n


@batch1("greedy")
def interval_scheduling(level: int, r: random.Random) -> Built:
    """Procedure: pick by earliest finish time (activity selection). structured: {"meetings": [[start, end]]} (integer times, start < end).
    Answer: the largest number of meetings one person can attend when no two attended meetings overlap (a meeting ending exactly when another starts does not overlap it).
    In 80% of items (drawn per item) neither choosing by earliest start nor choosing the shortest meeting first is optimal."""
    n = 8 + 2 * level + r.randint(0, 8)
    horizon = r.randint(25, 60) + 4 * level
    hard = r.random() < 0.8

    def shortest_first(iv: list[list[int]]) -> int:
        taken: list[list[int]] = []
        for a, b in sorted(iv, key=lambda x: (x[1] - x[0], x[0])):
            if all(b <= c or a >= d for c, d in taken):
                taken.append([a, b])
        return len(taken)

    def make() -> list[list[int]]:
        out = []
        for _ in range(n):
            s = r.randint(0, horizon - 2)
            out.append([s, s + r.randint(1, 6)])
        return out

    iv = until(500, make, lambda v: (not hard) or (earliest_start_greedy(v) != max_compatible(v) and shortest_first(v) != max_compatible(v)))
    ans = max_compatible(iv)
    text = "; ".join(f"meeting {i + 1} runs from {s} to {e}" for i, (s, e) in enumerate(iv))
    q = (f"A person can attend only one meeting at a time. Times are whole numbers of minutes: {text}. Two meetings clash if they share any stretch of time; "
         "a meeting that ends at the very minute another starts does not clash with it. What is the largest number of meetings the person can attend without any clash?")
    return Built(q, {"meetings": iv}, str(ans), "number", None)


def merge_cost(ws: list[int]) -> int:
    h = list(ws)
    heapq.heapify(h)
    total = 0
    while len(h) > 1:
        a, b = heapq.heappop(h), heapq.heappop(h)
        total += a + b
        heapq.heappush(h, a + b)
    return total


@batch1("greedy")
def merge_smallest_cost(level: int, r: random.Random) -> Built:
    """Procedure: repeatedly merge the two smallest (Huffman-style cost; ties do not change the total). structured: {"ws": [int]}.
    Answer: the total of the costs paid, each merge costing the sum of the two parts joined."""
    n = 4 + level
    ws = [r.randint(1, 9 + 4 * level) for _ in range(n)]
    ans = merge_cost(ws)
    if ans == sum(ws) * (n - 1) or ans == sum(ws):
        raise Retry
    q = (f"There are piles of stones with these sizes: {lst(ws)}. Two piles can be joined into one pile; joining costs as many coins as the size of the new pile. "
         "The piles are joined, two at a time, until one pile is left. What is the smallest total number of coins that can be paid?")
    return Built(q, {"ws": ws}, str(ans), "number", None)
