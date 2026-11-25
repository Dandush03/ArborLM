# ruff: noqa
"""Audit 4 (R2): alternative-reading key changes for wordings I judged open to a second reading. Seeds random.Random(f"a4r2-word|{lid}|{lv}") (throwaway).
count_divisible: 'the sum of the numbers in this list that are ...' read as a SET of values (repeats once) vs every entry.
Usage (cwd = audited worktree): PYTHONPATH=. uv run --locked --offline python a4_wording.py N"""
import random, sys
from studies.m0.core import build_item
from studies.m0.r2_fix3_set import fix3_set
N = int(sys.argv[1])
S = fix3_set()
lin = S["R2.count_divisible"]
for lv in range(7):
    r = random.Random(f"a4r2-word|count_divisible|{lv}")
    ch = 0
    for i in range(N):
        it = build_item(lin, lv, r, "A", "w")
        s = it.structured
        alt = sum(x for x in set(s["xs"]) if x % s["m"] == 0 and x > s["t"])
        ch += str(alt) != it.answer
    print(f"count_divisible L{lv}: set-of-values reading changes the key on {ch}/{N} = {ch/N:.3f}")
