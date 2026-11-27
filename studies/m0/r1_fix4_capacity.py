# ruff: noqa: E501
# mypy: disable-error-code="type-arg,no-untyped-call,no-any-return,arg-type,assignment,index,call-overload,var-annotated,list-item,unused-ignore,no-untyped-def"
"""Capacity of the surviving R1 shapes against ``core.generate_pool`` AS WRITTEN (lead rulings R-22, R-28, R-11, R-10, R-26).

``generate_pool`` balances over the LINEAGES of a part (not over clusters) and de-duplicates on the SHA-256 of the normalised question text, names included. It is called here unchanged; the only thing
replaced is where it finds the lineages of a part (``core.part_lineages`` is pointed at the surviving round-4 shapes of that part, because the shapes are not in ``core.REGISTRY``, R-9).
Demand per cluster and level (R-10, R-11): D = 10 x (ceil(4,000 / G) + ceil(20,000 / G) + 100). Two values of G are computed: G_total (the number of surviving clusters, as the round-4 brief reads it) and G_part
(the cluster count of the smaller part under the cluster-keys partition, as R-11 reads it); the pool is drawn for the larger demand, D(G_part) >= D(G_total), so a pass at D(G_part) is a pass at both.
Because the builder gives every lineage of a part the same quota, a cluster of m lineages receives m times the per-lineage quota; to guarantee the smallest cluster (m_min lineages) its demand D the per-lineage
quota is q = ceil(D / m_min) (a singleton cluster makes q = D, so every lineage must supply D distinct questions at every level). Each (part, level) is one ``generate_pool`` call with ``level_mix = {level: 1.0}``
and size = q x (lineages in the part); a lineage that cannot supply q distinct questions is recorded in ``shortfalls`` as (lineage, level, wanted, supplied) and the cell FAILS.
The result is a capacity under the reading 'two items are different if their normalised question texts differ' (names count); the structural readings (a) and (b) of round 3 are NOT recomputed here.
Run (worktree root): PYTHONHASHSEED=0 uv run --locked python -m studies.m0.r1_fix4_capacity <out.json> [pool seed] [workers]
"""

from __future__ import annotations

import json
import math
import sys
import time
from collections import Counter
from multiprocessing import Pool
from typing import Any

from studies.m0 import core
from studies.m0.lineages_r1_fix4_clusters import (
    cluster_table_v4,
    partition_readings_v4,
    registered_v4,
)


def demand(g: int) -> int:
    return 10 * (math.ceil(4000 / g) + math.ceil(20000 / g) + 100)


def parts() -> dict[str, Any]:
    """The surviving shapes per part under the cluster-keys partition (seed 400004), the clusters per part and the smallest cluster size (lineages) in each part."""
    lins = registered_v4()
    pm = partition_readings_v4(lins)["cluster_keys"]
    ct = cluster_table_v4(lins)
    out: dict[str, Any] = {}
    for p in ("A", "B"):
        cl = {k: sorted(x.id for x in v) for k, v in sorted(ct.items()) if pm[v[0].id] == p}
        out[p] = {"clusters": cl, "lineages": sorted(i for v in cl.values() for i in v), "m_min": min((len(v) for v in cl.values()), default=1)}
    return out


def _cell(args: tuple[str, int, int, int]) -> dict[str, Any]:
    part, level, q, seed = args
    lins = [x for x in registered_v4() if x.id in set(parts()[part]["lineages"])]
    saved = core.part_lineages
    core.part_lineages = lambda eval_id, p, partition_seed=400004: lins  # noqa: ARG005  (the surviving shapes of this part)
    shortfalls: list[tuple[str, int, int, int]] = []
    t0 = time.time()
    try:
        pool = core.generate_pool("R1", part, "development", seed, q * len(lins), {level: 1.0}, set(), shortfalls=shortfalls)
    finally:
        core.part_lineages = saved
    per = Counter(it.lineage for it in pool)
    problems = core.check_disjoint({"pool": pool})
    return {"part": part, "level": level, "per_lineage_quota": q, "lineages": len(lins), "items": len(pool), "supplied": dict(sorted(per.items())), "shortfalls": [list(s) for s in shortfalls],
            "text_repeats": len(problems), "seconds": round(time.time() - t0, 1)}


def main() -> None:
    out = sys.argv[1]
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 7500
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 6
    pt = parts()
    g_total = len(cluster_table_v4())
    g_part = min(len(pt[p]["clusters"]) for p in ("A", "B"))
    d_total, d_part = demand(g_total), demand(g_part)
    jobs = []
    for p in ("A", "B"):
        q = math.ceil(d_part / pt[p]["m_min"])
        jobs += [(p, lv, q, seed) for lv in range(7)]
    cells = []
    with Pool(workers) as pool:
        for c in pool.imap_unordered(_cell, jobs):
            cells.append(c)
            print(c["part"], c["level"], "items", c["items"], "shortfalls", len(c["shortfalls"]), c["seconds"], "s", flush=True)
    cells.sort(key=lambda c: (c["part"], c["level"]))
    res = {"G_total": g_total, "G_part": g_part, "D_total": d_total, "D_part": d_part, "pool_seed": seed, "parts": pt, "cells": cells}
    with open(out, "w") as f:
        json.dump(res, f, indent=1, sort_keys=True)


if __name__ == "__main__":
    main()
