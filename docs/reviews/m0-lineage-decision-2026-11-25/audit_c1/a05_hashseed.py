# ruff: noqa
"""Audit step 4c: does generation depend on the string hash seed? Prints one SHA-256 over 150 items per C1 cell.
Run twice with different PYTHONHASHSEED values and compare the printed digests (per lineage and overall)."""
import hashlib
import sys

sys.path.insert(0, ".")
from studies.m0.core import ALL_LEVELS, build_item, lineages_of, stream
from studies.m0.lineages_c1_common import load_batch1

lins = sorted(lineages_of("C1") + load_batch1(), key=lambda x: x.id)
tot = hashlib.sha256()
for lin in lins:
    h = hashlib.sha256()
    for lv in ALL_LEVELS:
        r = stream(777, "audit-hashseed", lin.id, str(lv))
        for i in range(150):
            it = build_item(lin, lv, r, "A", "x")
            h.update(it.question.encode() + b"\x00" + it.answer.encode() + b"\x01")
    print(lin.id, h.hexdigest()[:16])
    tot.update(h.digest())
print("ALL", tot.hexdigest())
