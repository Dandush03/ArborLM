# ruff: noqa: E501
"""C1 fix 4: capacity against ``core.generate_pool`` as written (ruling R-28).

``generate_pool`` allocates per lineage (``part_lineages``), per level (``allocate``), and for each (lineage, level) calls ``draw_items``: up to ``attempt_factor * count + 1000`` builds (attempt_factor 40), a
build is kept only if its normalised question text (NFKC, case-folded, whitespace collapsed; the question includes the program and so its identifiers) is not in ``taken``. This module calls the same
``core.draw_items`` for each (lineage, level) with ``count`` = the largest demand asked about and ``allow_short=True`` (as ``generate_pool`` does when a shortfall list is passed), with a fresh ``taken``
set per (lineage, level) (cross-lineage collisions of normalised question text are not simulated: different lineages write different programs). The number supplied is the capacity measured, capped at ``count``.

Demand per cluster and level (ruling R-11): 10 * (ceil(4000 / G) + ceil(20000 / G) + 100), with G the number of clusters of the smaller part, ``N // 2`` for N surviving clusters. A lineage passes a demand
if it supplies at least that many items at that level; a cluster passes if the sum over its members supplies at least that many (that is the reading under a per-cluster builder; under R-28 a lineage that
passes only that way is reported as such and is not counted as passing).

  uv run --locked python -m studies.m0.c1_fix4_capacity --ids <comma list> --count 35300 --seed 4242 --out <json> [--workers 8]
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from typing import Any


def demand(g: int) -> int:
    return 10 * (math.ceil(4000 / g) + math.ceil(20000 / g) + 100)


def one(args: tuple[str, int, int, int]) -> dict[str, Any]:
    from studies.m0.core import draw_items, stream
    from studies.m0.lineages_c1_fix4 import all_written

    lid, lv, count, seed = args
    lin = all_written()[lid]
    t = time.time()
    rng = stream(seed, "fix4-capacity", lid, str(lv))
    got = draw_items(lin, "A", lv, count, rng, set(), "capacity", allow_short=True)
    return {"lineage": lid, "level": lv, "wanted": count, "supplied": len(got), "reached": len(got) >= count, "seconds": round(time.time() - t, 1)}


def main() -> None:
    sys.path.insert(0, ".")
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", required=True)
    ap.add_argument("--count", type=int, required=True)
    ap.add_argument("--seed", type=int, default=4242)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    ids = a.ids.split(",")
    tasks = [(i, lv, a.count, a.seed) for i in ids for lv in range(7)]
    rows: list[dict[str, Any]] = []
    with ProcessPoolExecutor(a.workers) as ex:
        for r in ex.map(one, tasks):
            rows.append(r)
            print(r, flush=True)
    with open(a.out, "w") as f:
        json.dump({"count": a.count, "seed": a.seed, "rows": rows}, f, indent=1, sort_keys=True)


if __name__ == "__main__":
    main()
