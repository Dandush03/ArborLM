"""Extra facts: grid figures with enclosed holes / multiple components; percent-change items whose
intermediate prices are not whole cents (a per-step-rounding reading could differ)."""
import json
from fractions import Fraction
F = "/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_second_solver_fixtures_20261126/M1"
holes = comps_multi = 0
for line in open(f"{F}/M1.grid_perimeter_r3/fixtures.jsonl"):
    d = json.loads(line); cells = set()
    for r, runs in enumerate(d["structured"]["rows"]):
        for a, b in runs:
            for c in range(a, b + 1): cells.add((r, c))
    R = len(d["structured"]["rows"]); C = max(c for _, c in cells)
    # flood empty space from outside in a padded box
    seen = set(); st = [(-1, 0)]
    while st:
        p = st.pop()
        if p in seen or p in cells: continue
        r, c = p
        if r < -1 or r > R or c < 0 or c > C + 1: continue
        seen.add(p); st += [(r+1, c), (r-1, c), (r, c+1), (r, c-1)]
    empty_inside = [(r, c) for r in range(R) for c in range(1, C + 1) if (r, c) not in cells and (r, c) not in seen]
    if empty_inside: holes += 1; print("HOLE", d["level"], d["index"], empty_inside)
    seen = set(); k = 0
    for p in cells:
        if p in seen: continue
        k += 1; st = [p]
        while st:
            q = st.pop()
            if q in seen or q not in cells: continue
            seen.add(q); r, c = q; st += [(r+1, c), (r-1, c), (r, c+1), (r, c-1)]
    if k > 1: comps_multi += 1
print("grid items with enclosed holes:", holes, "; with more than one piece:", comps_multi, "of 280")
nc = []
for line in open(f"{F}/M1.percent_change_r3/fixtures.jsonl"):
    d = json.loads(line); p = Fraction(d["structured"]["price"]); inter = []
    for i, (dr, pc) in enumerate(d["structured"]["steps"]):
        p = p * (100 + (pc if dr == "up" else -pc)) / 100
        inter.append(p)
    if any((x * 100).denominator != 1 for x in inter[:-1]): nc.append((d["level"], d["index"], [str(x) for x in inter]))
print("percent items with a non-whole-cent intermediate price:", len(nc))
for x in nc: print("  ", x)
