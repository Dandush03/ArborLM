# ruff: noqa
"""Final R1 audit: reproducibility. For every survivor (and the two stage-2 drops) and level, 300 items at seed base B through the builders,
and one small core.generate_pool call per shape (part A label, level 3, 200 items, pool seed 8900); prints a SHA-256 per shape over
question, answer, answer_type, k and the structured fields (json, sort_keys) and over the pool's Item JSON (core.pool_hash).
Run in two fresh processes with different PYTHONHASHSEED and compare the outputs byte for byte.
usage: python repro_final.py <B>"""
import hashlib, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fgen
from studies.m0 import core
B = int(sys.argv[1])
C = fgen.candidates()
tot = hashlib.sha256()
for lid in sorted(C):
    h = hashlib.sha256()
    for lv in range(7):
        for b in fgen.items(C[lid], lv, 300, B):
            h.update(json.dumps([b.question, b.answer, b.answer_type, b.k, b.structured], sort_keys=True, default=repr).encode()); h.update(b"\n")
    core.part_lineages = lambda e, p, partition_seed=400004, l=C[lid]: [l]
    ph = core.pool_hash(core.generate_pool("R1", "A", "development", 8900, 200, {3: 1.0}, set()))
    print(lid, h.hexdigest(), "pool", ph)
    tot.update(h.hexdigest().encode() + ph.encode())
print("ALL", tot.hexdigest())
