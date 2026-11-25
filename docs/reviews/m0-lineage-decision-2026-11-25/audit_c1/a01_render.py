# ruff: noqa
"""Audit step 1: render 3 items per level for every C1 lineage (existing 14 + batch 25), read-only.

Uses only the generators (to obtain programs) and core.build_item / core.stream; no solver, no analysis module.
Run from the audited worktree: PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 uv run --locked --offline python <this> [ids...]
"""
import sys

sys.path.insert(0, ".")
from studies.m0.core import ALL_LEVELS, build_item, lineages_of, stream
from studies.m0.lineages_c1_common import load_batch1

SEED = 20261125
lins = {x.id: x for x in lineages_of("C1")}
lins.update({x.id: x for x in load_batch1()})
want = sys.argv[1:] or sorted(lins)
for lid in want:
    lin = lins[lid]
    print("=" * 30, lid, lin.family)
    for lv in ALL_LEVELS:
        r = stream(SEED, "audit-render", lid, str(lv))
        for k in range(3):
            it = build_item(lin, lv, r, "A", f"{lid}/{lv}/{k}")
            src = it.question.split("\n\n")[1]
            print(f"--- L{lv}#{k} -> {it.answer!r}")
            print(src)
