# ruff: noqa
"""Apply the author's lineage->part assignment (lineages_r1_clusters.partition over family_groups) to my cluster maps."""
import sys

sys.path.insert(0, "/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/arborlm-consolidation-experiment-2b31c1/experiments/_scratch/m0_lineage_audit2_r1_20261125")
from registry import registered  # noqa: E402
from my_clusters import components, PRIMARY, BORDER  # noqa: E402
from studies.m0 import lineages_r1_clusters as C  # noqa: E402

reg = registered()
ids = sorted(reg)
fg, part = C.family_groups(), C.partition()
lp = {i: part[fg[reg[i].family]] for i in ids}
for name, edges in (("PRIMARY", PRIMARY), ("STRICTEST", PRIMARY + BORDER)):
    comps = components(ids, edges)
    a = sum(1 for c in comps if {lp[x] for x in c} == {"A"})
    b = sum(1 for c in comps if {lp[x] for x in c} == {"B"})
    s = [c for c in comps if len({lp[x] for x in c}) == 2]
    print(f"{name}: {len(comps)} clusters; wholly A {a}, wholly B {b}, straddling {len(s)}")
    for c in s:
        print("   ", [(x[3:], lp[x]) for x in c])
