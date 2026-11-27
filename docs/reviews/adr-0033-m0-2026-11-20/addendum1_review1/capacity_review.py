# ruff: noqa
"""Addendum 1 section 10: capacity demand per cluster and level, recomputed by the reviewer.
(i) the drafter's formula 10 * (ceil((4,000 + 20,000)/G) + 100);
(ii) dev and sealed pools each spread evenly by largest remainder, so the largest cluster holds
     ceil(4,000/G) + ceil(20,000/G): 10 * (ceil(4000/G) + ceil(20000/G) + 100);
(iii) the reserve level if it can carry the registered level mix (ADR-0033 section 6.5: after the reserve levels are
     scored "the rule is applied again"): the same as a core level instead of 10 * 100.
Run: uv run --locked python docs/reviews/adr-0033-m0-2026-11-20/addendum1_review1/capacity_review.py
"""
import math
for G in (8, 11, 13, 14, 15, 19, 300):
    a = 10 * (math.ceil(24000 / G) + 100)
    b = 10 * (math.ceil(4000 / G) + math.ceil(20000 / G) + 100)
    print(f"G={G}: drafter {a:,}; separate ceilings {b:,} (diff {b - a}); reserve level as drafted 1,000, if it can carry the mix {b:,}")
