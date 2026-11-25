# ruff: noqa
"""Audit 3 (R1): how often the answer is stated verbatim. conditional_chain: the asked variable is one of the stated facts;
pet_owners: "X owns the <asked pet>." is a clue; seating_row: "X sits in seat <asked seat>." is a clue. 1,000 items per level,
seed base 5200 (the battery's draw). This is the saved form of the inline command whose output is verbatim_run1.txt.
usage (worktree root): PYTHONHASHSEED=0 uv run --locked python <this>"""
import os, sys
from collections import Counter
sys.path.insert(0, os.path.dirname(__file__))
import gen

L = gen.lineages()
for lv in range(7):
    its = gen.items(L["R1.conditional_chain"], lv, 1000, 5200)
    f = sum(1 for b in its if b.structured["query"] in [v for v, _ in b.structured["facts"]])
    print("cond_chain L", lv, "query stated as a fact:", f, "/1000; keys", dict(Counter(b.answer for b in its)))
for lv in range(7):
    its = gen.items(L["R1.pet_owners"], lv, 1000, 5200)
    f = sum(1 for b in its if any(c[0] == "owns" and c[2] == b.structured["ask"] for c in b.structured["clues"]))
    its2 = gen.items(L["R1.seating_row"], lv, 1000, 5200)
    g = sum(1 for b in its2 if any(c[0] == "pos" and c[2] == b.structured["seat"] for c in b.structured["clues"]))
    print("L", lv, "pet_owners asked pet stated verbatim", f, "/1000; seating asked seat stated verbatim", g, "/1000")
