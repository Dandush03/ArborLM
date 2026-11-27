# ruff: noqa
"""Final R1 audit: capacity against core.generate_pool AS WRITTEN (R-28, R-30).
Demand per cluster and level: D(G) = 10 x (ceil(4000/G) + ceil(20000/G) + 100), G = clusters of the smaller part = floor(surviving clusters / 2).
generate_pool gives every lineage of a part the same quota, and every cluster here has a single-lineage member or is itself a singleton... the
quota needed so that the SMALLEST cluster (fewest lineages, m_min) reaches D is q = ceil(D / m_min) per lineage and level.
The set's shapes are not in core.REGISTRY (core.lineages_of('R1') returns the 15 pre-fix lineages), so core.part_lineages is pointed at
the shapes (one lineage per call). Equivalence with a whole-part call: generate_pool derives each lineage's stream from
(seed, role, salt, eval, part, lineage id, level) only, so a lineage draws the same items whatever else is in the part; the one shared
state is `taken` (text hashes), and cross-lineage repeats are checked here afterwards over every lineage of the part and level.
Pass = no shortfall and q distinct normalised texts (core.text_hash) for every lineage, and no repeat across the part.
usage: python capacity_final.py <set: 12|11> <G csv> <pool seed> <workers> <out.json>"""
import json, math, os, sys, time
from collections import Counter
from multiprocessing import Pool
W = "/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f"
sys.path.insert(0, W)
from studies.m0 import core
from studies.m0.lineages_r1_fix4_clusters import registered_v4, cluster_table_v4, partition_readings_v4

DROP_MINE = {"R1.graph_shortest_route_r6"}


def the_set(name):
    ls = registered_v4()
    return ls if name == "12" else [x for x in ls if x.id not in DROP_MINE]


def demand(g):
    return 10 * (math.ceil(4000 / g) + math.ceil(20000 / g) + 100)


def cell(args):
    setname, lid, part, level, q, seed = args
    lin = next(x for x in the_set(setname) if x.id == lid)
    core.part_lineages = lambda eval_id, p, partition_seed=400004: [lin]
    sf = []
    t0 = time.time()
    pool = core.generate_pool("R1", part, "development", seed, q, {level: 1.0}, set(), shortfalls=sf)
    hs = [core.text_hash(it.question) for it in pool]
    return {"lineage": lid, "part": part, "level": level, "q": q, "supplied": len(pool), "distinct": len(set(hs)), "shortfalls": sf,
            "seconds": round(time.time() - t0, 1), "h8": [int(h[:16], 16) for h in hs]}


if __name__ == "__main__":
    setname, gs, seed, workers, outp = sys.argv[1], [int(x) for x in sys.argv[2].split(",")], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
    ls = the_set(setname)
    ct = cluster_table_v4(ls)
    pm = partition_readings_v4(ls)["cluster_keys"]
    parts = {p: {k: sorted(x.id for x in v) for k, v in sorted(ct.items()) if pm[v[0].id] == p} for p in "AB"}
    gpart = min(len(parts["A"]), len(parts["B"]))
    res = {"set": setname, "shapes": sorted(x.id for x in ls), "clusters": len(ct), "G_by_R30": len(ct) // 2, "G_smaller_part": gpart, "parts": parts, "pool_seed": seed, "runs": {}}
    for g in gs:
        D = demand(g)
        jobs = []
        for p in "AB":
            mmin = min(len(v) for v in parts[p].values())
            q = math.ceil(D / mmin)
            for k, members in parts[p].items():
                for lid in members:
                    for lv in range(7):
                        jobs.append((setname, lid, p, lv, q, seed))
        cells, cross = [], Counter()
        seen = {}
        with Pool(workers) as pool:
            for c in pool.imap_unordered(cell, jobs):
                key = (c["part"], c["level"])
                s = seen.setdefault(key, set())
                hs = set(c.pop("h8"))
                cross[key] += len(s & hs)
                s |= hs
                cells.append(c)
                print(f"G={g} D={D} {c['lineage']} {c['part']} L{c['level']} q={c['q']} supplied={c['supplied']} distinct={c['distinct']} short={len(c['shortfalls'])} {c['seconds']}s", flush=True)
        del seen
        cells.sort(key=lambda c: (c["part"], c["lineage"], c["level"]))
        per_cluster = {}
        for p in "AB":
            for k, members in parts[p].items():
                for lv in range(7):
                    sup = sum(c["distinct"] for c in cells if c["lineage"] in members and c["level"] == lv)
                    per_cluster.setdefault(k, {})[lv] = {"supplied": sup, "demand": D, "pass": sup >= D and not any(c["shortfalls"] for c in cells if c["lineage"] in members and c["level"] == lv)}
        res["runs"][str(g)] = {"D": D, "cells": cells, "cross_lineage_repeats": {f"{p}L{lv}": n for (p, lv), n in sorted(cross.items())},
                               "per_cluster": per_cluster, "all_pass": all(v["pass"] for d in per_cluster.values() for v in d.values()) and sum(cross.values()) == 0,
                               "shortfall_cells": sum(1 for c in cells if c["shortfalls"]), "within_cell_repeats": sum(c["supplied"] - c["distinct"] for c in cells)}
        print(f"G={g} D={D} all_pass={res['runs'][str(g)]['all_pass']} shortfall_cells={res['runs'][str(g)]['shortfall_cells']} cross={sum(cross.values())}", flush=True)
    json.dump(res, open(outp, "w"), indent=1, sort_keys=True)
