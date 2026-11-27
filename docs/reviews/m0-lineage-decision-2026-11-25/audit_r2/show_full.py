# ruff: noqa
"""Print full rendered questions of named lineages from any registry (auditor seed). Read-only."""
import sys
from studies.m0.core import build_item, lineages_of, stream
from studies.m0 import lineages_r1_common, lineages_c1_common, lineages_m1_common, lineages_r2_common
allx = {}
for l in [*lineages_of("R1"), *lineages_r1_common.load_pilot(), *lineages_of("C1"), *lineages_c1_common.load_batch1(), *lineages_of("M1"), *lineages_m1_common.load_batch(), *lineages_of("R2"), *lineages_r2_common.load_batch1()]:
    allx[l.id] = l
lv = int(sys.argv[1])
for lid in sys.argv[2:]:
    it = build_item(allx[lid], lv, stream(777125, "full", lid), "A", "x")
    print(f"=== {lid}\n{it.question}\n=> {it.answer}\n")
