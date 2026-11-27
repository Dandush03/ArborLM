# ruff: noqa
"""Auditor: realised shape / ask mix per level (rejection inside a builder redraws the shape too, so the nominal uniform mix can collapse).
Run from the audited worktree: PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 PYTHONPATH=. uv run --locked --offline python <this> [N]"""
import sys
from collections import Counter
from studies.m0.core import ALL_LEVELS, build_item, stream
from studies.m0.lineages_m1_common import load_batch
N = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
FIELD = {"M1.gcd_lcm": "ask", "M1.binomial_choose": "shape", "M1.quadratic_area": "shape", "M1.division_counting": "shape", "M1.inclusion_exclusion": "ask",
         "M1.pythagoras": "shape", "M1.prime_factors": "ask", "M1.recurrence_iterate": "shape", "M1.median_list": "shape", "M1.mode_tally": "ask",
         "M1.pigeonhole_worst_case": "goal", "M1.tiered_pricing": "mode", "M1.painted_cube": "faces", "M1.last_digit_power": "op", "M1.slot_permutations": "parity"}
for lin in load_batch():
    if lin.id not in FIELD:
        continue
    row = []
    for lv in ALL_LEVELS:
        r = stream(777011, "shape-mix", lin.id, str(lv))
        c = Counter(str(build_item(lin, lv, r, "A", "x").structured[FIELD[lin.id]]) for _ in range(N))
        row.append(f"L{lv} " + ",".join(f"{k}:{v/N:.2f}" for k, v in sorted(c.items())))
    print(lin.id, FIELD[lin.id], " | ".join(row), flush=True)
