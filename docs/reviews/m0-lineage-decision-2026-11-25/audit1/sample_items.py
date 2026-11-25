# ruff: noqa
# ruff: noqa
"""Auditor sampler: 3 items per level (0..6) for each of the 35 R1 lineages.

Old 15: rendered by calling their builders (read-only import) with the
auditor's own seed stream. New 20: sampled from the committed fixtures.
Writes one text file per lineage beside this script (samples/).
Usage: python sample_items.py <agent worktree root> <out dir>
"""
import json
import os
import random
import sys

root, out = sys.argv[1], sys.argv[2]
sys.path.insert(0, root)
from studies.m0 import core  # noqa: E402
from studies.m0 import lineages_r1  # noqa: E402,F401

os.makedirs(out, exist_ok=True)
AUD_SEED = 20261125

old = [l for l in core.REGISTRY["R1"]]
print("old lineages:", len(old))
for lin in sorted(old, key=lambda x: x.id):
    lines = []
    for lv in range(7):
        rng = random.Random(f"{AUD_SEED}|{lin.id}|{lv}")
        for k in range(3):
            it = core.build_item(lin, lv, rng, "X", f"{lin.id}/audit/L{lv}/{k}")
            lines.append(json.dumps({"id": it.id, "level": lv, "question": it.question, "answer": it.answer, "structured": it.structured}, sort_keys=True))
    open(os.path.join(out, lin.id + ".jsonl"), "w").write("\n".join(lines) + "\n")

fx = os.path.join(root, "studies/m0/fixtures/r1_pilot")
new = sorted(f for f in os.listdir(fx) if f.endswith(".jsonl"))
print("new lineages:", len(new))
for f in new:
    rows = [json.loads(x) for x in open(os.path.join(fx, f))]
    rng = random.Random(f"{AUD_SEED}|{f}")
    lines = []
    for lv in range(7):
        pool = [x for x in rows if x["level"] == lv]
        for x in rng.sample(pool, 3):
            lines.append(json.dumps({"id": x["id"], "level": lv, "question": x["question"], "answer": x["answer"], "structured": x["structured"]}, sort_keys=True))
    open(os.path.join(out, f), "w").write("\n".join(lines) + "\n")
