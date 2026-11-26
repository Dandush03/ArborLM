"""Write the 469 round-1 cells (lineage, level, round-1 target D_lin(G, k_c)) split into text and C1 lists."""
import json
import sys

sys.path.insert(0, "/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_capacity_recompute_20261126/deliver")
import rc_common as rc  # noqa: E402

parts = rc.round1_parts()
text, c1 = [], []
for (e, p), cls in sorted(parts.items()):
    G = len(cls)
    for c, lids in sorted(cls.items()):
        t = rc.D_lin(G, len(lids))
        for lid in lids:
            for lv in rc.LEVELS:
                (c1 if e == "C1" else text).append([lid, lv, t])
json.dump(text, open(f"{rc.SCR}/work/round1_cells_text.json", "x"))
json.dump(c1, open(f"{rc.SCR}/work/round1_cells_c1.json", "x"))
print(len(text), len(c1), len(text) + len(c1), "attempts at least", sum(c[2] for c in text + c1))
