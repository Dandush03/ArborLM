# ruff: noqa
"""Final R2 audit: from_base digit-count and base distribution per level (text only), and examples of texts shared between L0 and L1.
Usage (cwd = audited worktree): PYTHONPATH=. PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 uv run --locked --offline python <this>"""
import random, re
from collections import Counter
from studies.m0.core import build_item
from studies.m0.r2_fix4_set import fix4_set
lin = fix4_set()["R2.from_base"]
T = {}
for lv in range(7):
    r = random.Random(f"finalr2-lv|R2.from_base|{lv}")
    c = Counter(); texts = set()
    for _ in range(1000):
        q = build_item(lin, lv, r, "A", "x").question
        b, d = re.search(r"base-(\d+) number ([0-9a-z]+)", q).groups()
        c[len(d)] += 1; texts.add(q)
    T[lv] = texts
    print(lv, "digits:", sorted(c.items()))
sh = sorted(T[0] & T[1])
print("shared L0/L1:", len(sh)); print("\n".join(sh[:5]))
