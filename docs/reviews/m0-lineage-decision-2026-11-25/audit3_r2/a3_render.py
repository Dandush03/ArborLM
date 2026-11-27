# ruff: noqa
"""Audit 3 (R2): render items for reading. Seed random.Random(f"a3r2-render|{lid}|{lv}|3")."""
import random
import sys

from studies.m0.core import build_item
from a3_set import current

levels = [int(x) for x in sys.argv[1].split(",")] if len(sys.argv) > 1 else [1]
per = int(sys.argv[2]) if len(sys.argv) > 2 else 1
for lid, lin in current().items():
    for lv in levels:
        r = random.Random(f"a3r2-render|{lid}|{lv}|3")
        for i in range(per):
            it = build_item(lin, lv, r, "A", "x")
            print(f"### {lid} L{lv} #{i}\nQ: {it.question}\nA: {it.answer}  ({it.answer_type}, k={it.k})\n")
