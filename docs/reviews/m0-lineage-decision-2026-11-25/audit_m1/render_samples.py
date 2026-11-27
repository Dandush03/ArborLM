# ruff: noqa
"""Auditor throwaway: render 3 items per level for all 37 M1 lineages (16 registered + 21 batch). Read-only on the repo.

Run from the audited worktree:
  PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 PYTHONPATH=. uv run --locked --offline python <this> > samples.txt
"""
import sys
from studies.m0.core import build_item, lineages_of, stream, ALL_LEVELS
from studies.m0.lineages_m1_common import load_batch

SEED = 777001  # auditor's own seed, unrelated to any registered seed
lins = lineages_of("M1") + load_batch()
print(f"# {len(lins)} lineages", file=sys.stderr)
for lin in lins:
    print(f"==== {lin.id} (family {lin.family})")
    for lv in ALL_LEVELS:
        r = stream(SEED, "audit-render", lin.id, str(lv))
        for i in range(3):
            it = build_item(lin, lv, r, "A", f"{lin.id}/{lv}/{i}")
            print(f"L{lv}.{i} [{it.answer}] {it.question}")
