# ruff: noqa
"""List every lineage of R1, C1, M1 (core registry + their batch registries) with one rendered question (truncated),
for the cross-evaluation duplicate check. Read-only; auditor seed."""
import sys

from studies.m0.core import build_item, lineages_of, stream
from studies.m0 import lineages_r1_common, lineages_c1_common, lineages_m1_common

SEED = 777124
groups = {
    "R1-core": lineages_of("R1"),
    "R1-pilot": lineages_r1_common.load_pilot(),
    "C1-core": lineages_of("C1"),
    "C1-batch1": lineages_c1_common.load_batch1(),
    "M1-core": lineages_of("M1"),
    "M1-batch": lineages_m1_common.load_batch(),
}
width = int(sys.argv[1]) if len(sys.argv) > 1 else 260
for g, lins in groups.items():
    print(f"##### {g}: {len(lins)}")
    for lin in lins:
        it = build_item(lin, 3, stream(SEED, "xeval", lin.id), "A", "x")
        q = it.question.replace("\n", " | ")
        print(f"{lin.id} [{lin.family}] :: {q[:width]} => {it.answer[:40]}")
