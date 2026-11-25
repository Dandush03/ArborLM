# ruff: noqa
"""Audit 3 (C1), step 9: capacity table per lineage and per cluster (my strict map, and the author's map) at worst-case demand.
python a9_capacity_table.py a6_capacity_seed11.json
need(G) = 10 * (ceil(24,000 / G) + 100) on core levels 1-5; reserve levels 0 and 6: 1,000 (standing reading) and, as a second
reading, the core need (if calibration ever selects a reserve level, ADR 6.5).  Cluster capacity = sum of its members' counts.
K1 counts stop at the draw target (25,000), so 'K1 >= need' is decided for every need <= 25,000.  K2 counts are LOWER BOUNDS when the
cell stopped at the K1 target; when the cell exhausted its draw budget they are near-saturated (late new-class rate printed)."""
import json, math, sys

d = json.load(open(sys.argv[1]))
rows = d["rows"]
need = lambda G: 10 * (math.ceil(24000 / G) + 100)
GS = (10, 11, 14, 15, 20)
MINE = {
    "B1": ["C1.list_build", "C1.loop_sum", "C1.nested_pairs", "C1.string_build"], "B2": ["C1.func_branch", "C1.func_compose"],
    "B3": ["C1.slices", "C1.string_methods"], "B4": ["C1.coin_change_table", "C1.grid_path_table", "C1.string_pair_table"],
    "B5": ["C1.cond_chain", "C1.euclid_gcd", "C1.euclid_gcd_traced"], "B6+": ["C1.fib_like", "C1.fib_shapes_recursive", "C1.recursive_calls_r2"],
    "B7": ["C1.bytecode_loop_r2", "C1.turtle_walk_r2"], "B8": ["C1.bracket_matching", "C1.postfix_evaluation", "C1.bracket_matching_traced"],
    "insertion": ["C1.insertion_sort", "C1.insertion_sort_traced"], "fast_power": ["C1.fast_power_r2", "C1.fast_power_traced"],
    "kadane": ["C1.kadane_scan", "C1.kadane_scan_traced"],
}
inany = {m for v in MINE.values() for m in v}
for lid in sorted(rows):
    if lid not in inany:
        MINE[lid] = [lid]


def late_rate(c):
    cps = sorted((int(k), v) for k, v in c["checkpoints"].items())
    if len(cps) < 2:
        return None
    (a, va), (b, vb) = cps[-2], cps[-1]
    return round((vb[0] - va[0]) / max(1, b - a), 3), round((vb[1] - va[1]) / max(1, b - a), 3)


print("## Per lineage and level: K1 (names do not count) / K2 (literals that do not change control flow do not count); * = draw budget exhausted")
print("lineage | " + " | ".join(f"L{l} K1/K2" for l in range(7)))
for lid in sorted(rows):
    cells = []
    for l in range(7):
        c = rows[lid][str(l)]
        cells.append(f"{c['K1']}/{c['K2']}{'*' if not c['reached_target'] else ''}")
    print(lid + " | " + " | ".join(cells))
print()
for crit in ("K1", "K2"):
    print(f"## Failing cells under {crit}, per CLUSTER (my strict map incl. the PROPOSED traced shapes in their clusters), core levels 1-5")
    for G in GS:
        fails = []
        for cl, mem in sorted(MINE.items()):
            for l in range(1, 6):
                cap = sum(rows[m][str(l)][crit] for m in mem if m in rows)
                if cap < need(G):
                    fails.append(f"{cl}:L{l}={cap}")
        print(f"G={G} need={need(G)}: {len(fails)} failing cluster-levels of {len(MINE) * 5}: {', '.join(fails)}")
    print()
print("## Reserve levels 0 and 6 (K1): vs 1,000 and vs the core need at G=14 (18,150), per cluster")
for cl, mem in sorted(MINE.items()):
    for l in (0, 6):
        cap = sum(rows[m][str(l)]["K1"] for m in mem if m in rows)
        if cap < 18150:
            print(f"  {cl} L{l}: K1={cap} {'FAILS 1,000' if cap < 1000 else 'passes 1,000'}; fails 18,150")
print()
print("## Per LINEAGE failing core cells (K1), in case the pool is allocated per lineage rather than per cluster (code: generate_pool allocates per lineage)")
for G in (14, 15, 20):
    fails = [f"{lid}:L{l}={rows[lid][str(l)]['K1']}" for lid in sorted(rows) for l in range(1, 6) if rows[lid][str(l)]["K1"] < need(G)]
    print(f"G={G} need={need(G)}: {len(fails)}: {', '.join(fails)}")
print()
print("## Late new-class rates (K1, K2 per draw over the last checkpoint interval) for budget-exhausted cells")
for lid in sorted(rows):
    for l in range(7):
        c = rows[lid][str(l)]
        if not c["reached_target"]:
            print(f"  {lid} L{l}: draws {c['draws']} K1 {c['K1']} (chao1 {c['K1_chao1']}) K2 {c['K2']} late {late_rate(c)}")
