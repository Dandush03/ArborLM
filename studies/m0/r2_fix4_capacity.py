# ruff: noqa: E501
"""R2 fix round 4: capacity against ``core.generate_pool`` AS WRITTEN (R-28), for the lineages that survive the shortcut, wording and level checks.

Demand per cluster and level (R-11, brief): D(G) = 10 x (ceil(4000/G) + ceil(20000/G) + 100), G = the number of surviving clusters. For each lineage the module calls ``core.generate_pool`` itself (``core.part_lineages`` is replaced
inside the worker by a function that returns just that lineage, so the builder, ``allocate``, ``draw_items`` with its attempt limit of 40 x count + 1000 and the text-hash de-duplication across the levels of one pool are those of core),
with size 7 x D and a uniform level mix over levels 0-6, so that each level has to supply D items with new normalised question texts; ``shortfalls`` records (lineage, level, wanted, supplied). The text hash includes names,
so this is the 'text' reading of a distinct item; nothing is relabelled. One pool per lineage: texts shared BETWEEN lineages are not de-duplicated here (different templates; not measured).
A lineage that supplies less than D at some level FAILS as written. If the sum of the supplied counts of the members of its cluster reaches D at that level, the cluster would pass under a per-cluster builder; that is reported separately and
is not counted as passing (R-28). Seeds: throwaway integer 424242, role 'cap'. Self-check, not independent review.
Usage: ``PYTHONHASHSEED=0 uv run --locked --offline python -m studies.m0.r2_fix4_capacity run --g 18 --names a,b,c --out OUT.json --procs 10``."""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from multiprocessing import Pool
from pathlib import Path
from typing import Any

SEED = 424242
LEVELS = (0, 1, 2, 3, 4, 5, 6)


def demand(g: int) -> int:
    return 10 * (math.ceil(4000 / g) + math.ceil(20000 / g) + 100)


def run_one(args: tuple[str, int]) -> tuple[str, dict[str, Any]]:
    lid, d = args
    from studies.m0 import core
    from studies.m0.r2_fix4_set import fix4_set

    lin = fix4_set()[lid]
    original = core.part_lineages
    core.part_lineages = lambda eval_id, part, seed=400004: [lin]  # type: ignore[assignment]  # the pool builder as written, restricted to this one lineage
    short: list[tuple[str, int, int, int]] = []
    t0 = time.time()
    try:
        pool = core.generate_pool("R2", "A", "cap", SEED, d * len(LEVELS), {lv: 1.0 for lv in LEVELS}, set(), shortfalls=short)
    finally:
        core.part_lineages = original  # restored: a caller in the same process (a test) must not keep the patched function
    per_level = {str(lv): sum(1 for it in pool if it.level == lv) for lv in LEVELS}
    for _lid, lv, _want, got in short:
        per_level[str(lv)] = got
    return lid, {"demand": d, "supplied": per_level, "shortfalls": [list(x) for x in short], "seconds": round(time.time() - t0, 1)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("run",))
    ap.add_argument("--g", type=int, required=True)
    ap.add_argument("--names", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--procs", type=int, default=8)
    a = ap.parse_args()
    d = demand(a.g)
    ids = [f"R2.{n}" for n in a.names.split(",")]
    with Pool(a.procs) as p:
        res = dict(p.map(run_one, [(i, d) for i in ids], chunksize=1))
    a.out.write_text(json.dumps({"g": a.g, "demand": d, "seed": SEED, "lineages": res}, indent=1, sort_keys=True))
    print("wrote", a.out, "demand", d, file=sys.stderr)


if __name__ == "__main__":
    main()
