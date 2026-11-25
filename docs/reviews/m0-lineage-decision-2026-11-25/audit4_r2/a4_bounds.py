# ruff: noqa
"""Audit 4 (R2): cluster counts under shortcut bounds 0.10 / 0.15 / 0.25 on MY strict map, with my NEEDS-FIX lineages excluded, then capacity at the resulting G
(only the surviving members of a cluster count towards its capacity). Uses a4_summ2.klass for the rule classes.
Usage: python3 -I a4_bounds.py a4_shortcuts_2000.json a4_capacity_100k.json"""
import json
import math
import sys

sys.argv_saved = list(sys.argv)
sc = json.load(open(sys.argv[1]))
cap = json.load(open(sys.argv[2]))
sys.argv = [sys.argv[0], sys.argv[1]]
import io, contextlib

with contextlib.redirect_stdout(io.StringIO()):
    import a4_summ2 as S  # computes S.table on import (prints suppressed)

NEEDS_FIX = {"count_letter", "gcd_euclid", "max_subarray_sum", "palindrome_check", "permutation_power", "subtraction_game", "multiples_between"}
MERGES = [("sort_list", "kth_smallest"), ("count_letter", "count_divisible"), ("to_base_wide", "from_base"), ("permutation_power", "modular_power")]
ids = sorted(x.split(".")[1] for x in sc["lineages"])
cl = {i: [i] for i in ids}
for a, b in MERGES:
    cl[a] = cl[a] + cl.pop(b)


def mx(name, classes):
    t = S.table["R2." + name]
    return max(t[c][L][0] for c in classes for L in range(7))


for label, classes in (("cues only", ("cue",)), ("cues + partial", ("cue", "partial")), ("cues + partial + construct", ("cue", "partial", "construct"))):
    for bound in (0.10, 0.15, 0.25):
        keep = {k: [m for m in mem if m not in NEEDS_FIX and mx(m, classes) <= bound + 1e-12] for k, mem in cl.items()}
        keep = {k: v for k, v in keep.items() if v}
        n = len(keep)
        G = n // 2
        need = 10 * (math.ceil(4000 / G) + math.ceil(20000 / G) + 100) if G else None
        fails = {rd: [] for rd in "abc"}
        for rd in "abc":
            for k, mem in keep.items():
                for lv in range(7):
                    D = sum(cap["lineages"]["R2." + m][str(lv)][rd]["D"] for m in mem)
                    C = sum(cap["lineages"]["R2." + m][str(lv)][rd]["chao1"] for m in mem)
                    if D < need:
                        fails[rd].append(f"{k} L{lv} D={D} Chao1={C:.0f}" + (" (D = draws: unresolved, more draws needed)" if C >= need else ""))
        print(f"[{label}] bound {bound:.2f}: {n} clusters -> parts {n - n // 2}/{G}, G = {G}, demand {need}")
        print("    clusters:", sorted(keep))
        for rd in "abc":
            print(f"    capacity reading {rd}: {len(fails[rd])} failing cluster-levels" + (": " + "; ".join(fails[rd][:12]) + (" ..." if len(fails[rd]) > 12 else "") if fails[rd] else ""))
