# ruff: noqa
"""Audit 4 (R1): categories_follow_r5 plantings per item by drawn (kind, class): wraps the module-level _plant_categories (read-only
monkeypatch in this process) to count calls; and the share of plantings rejected for each reason, recomputed with the module's own closure.
usage (implementation worktree root): PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 uv run --locked python <this> <n_per_level>"""
import os, sys, random
from collections import Counter, defaultdict
sys.path.insert(0, os.path.dirname(__file__))
import gen4
from studies.m0 import lineages_r1_fix3_e as E
orig = E._plant_categories
calls = Counter()
def wrapped(r, level, kind, want):
    calls[(kind, want)] += 1
    return orig(r, level, kind, want)
E._plant_categories = wrapped
lin = gen4.lineages()["R1.categories_follow_r5"]
n = int(sys.argv[1])
items = Counter()
for lv in range(7):
    for b in gen4.items(lin, lv, n, 8200):
        items[(b.structured["kind"], b.answer)] += 1
for k in sorted(items):
    print(f"kind={k[0]:5s} class={k[1]:22s} items={items[k]:5d} plantings={calls[k]:6d} per item={calls[k] / items[k]:.2f}")
