"""Replay chosen trials of check_rules.py and print the perturbed cells (diagnosis of disagreements)."""
import random, sys, json
from pathlib import Path
sys.argv = [sys.argv[0], sys.argv[1]] + sys.argv[2:]
PIN = sys.argv[1]
sys.path.insert(0, str(Path(__file__).parent))
import check_rules as K
want = set(int(x) for x in sys.argv[2].split(","))
rng = random.Random(229501)
for t in range(max(want) + 1):
    n = rng.choice([3, 4])
    base, cells = K.scenario(rng, n)
    if t in want:
        print("trial", t, "n", n, "base", base)
        for (r, g, v), c in cells.items():
            tmpl = K.TEMPLATE[(g, v)]
            tp = {"E_A": tmpl[0], "E_B": tmpl[1]}
            dif = []
            if c.panels != tp: dif.append(("panels", c.panels))
            if g in K.MEMORY:
                ta = {p: {"unablated": tp[p], "value_perm": 0.05, "code_perm": 0.08, "marker_only": 0.1} for p in ("E_A", "E_B")}
                if c.abl != ta: dif.append(("abl", c.abl))
            if g in K.GEN and c.gen != 0.001: dif.append(("gen", c.gen))
            if c.status != "completed": dif.append(("status", c.status))
            if c.rejected or c.below_floor: dif.append(("flags", c.rejected, c.below_floor))
            if dif: print("  ", (r, g, v), dif)
