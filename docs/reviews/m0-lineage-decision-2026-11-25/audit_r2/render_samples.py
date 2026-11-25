# ruff: noqa
"""Render 3 items per level for every R2 lineage (16 existing from core.REGISTRY + 26 batch-1). Read-only; uses the
generators only to draw items with an auditor-chosen seed (not any registered seed). Output to stdout."""
import json
import sys

from studies.m0.core import ALL_LEVELS, build_item, lineages_of, stream
from studies.m0.lineages_r2_common import load_batch1

SEED = 777123  # auditor's own, not a registered seed
existing = lineages_of("R2")
new = load_batch1()
full = "--full" in sys.argv
print(f"existing={len(existing)} new={len(new)}")
for lin in [*existing, *new]:
    print(f"=== {lin.id} family={lin.family}")
    for lv in ALL_LEVELS:
        r = stream(SEED, "audit-render", lin.id, str(lv))
        for i in range(3):
            it = build_item(lin, lv, r, "A", f"{lin.id}/{lv}/{i}")
            if full and lv == 3 and i == 0:
                print(f"  FULL L{lv}: {it.question}  => {it.answer}")
            print(f"  L{lv}.{i} {json.dumps(it.structured, sort_keys=True)[:230]} => {it.answer}")
