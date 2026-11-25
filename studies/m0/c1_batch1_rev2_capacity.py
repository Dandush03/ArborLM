# ruff: noqa: E501
"""Structural capacity of the CURRENT C1 lineages at the G actually written (lead ruling R-5; measurement, no new threshold).

Structure means: distinct programs after every identifier is renamed by first appearance (``c1_batch1_capacity.alpha_key``); a change of names alone is not a
distinct item. The demand follows ``ggen.demand_per_level`` / ``lineage_gates.demand_at_g`` with the registered factor 10, at G = the number of lineages written
for C1 divided by the two parts.

G written. ``lineages_c1_clusters.current_ids()`` lists the lineages in force (40: the old 14 and batch 1's 25 less the 8 superseded, plus 9 revised ones; the
PROPOSED traced shapes are shapes of existing clusters and not counted). G per part is that number halved: 20. (If the strict clusters of the audit are the
unit, 29 clusters, G per part is 14.5, so about 15; the demand is then larger and is printed too.)

Demand per lineage and level, pools of one part = 4,000 development + 20,000 sealed items, tuning draw 100 per level (``lineage_gates``):
  even   (the pools spread evenly over the five core levels, the audit's reading):  ceil(24,000 / G_part / 5) + 100
  worst  (the whole part on one level, the reading ``ggen``/``lineage_gates`` use):  ceil(24,000 / G_part) + 100
Reserve levels demand the tuning draw only. Needed capacity is 10 times the demand. At G_part = 20: even 340 -> 3,400; worst 1,300 -> 13,000 (the worst
reading is NOT exhibited here: it would need 40,000-draw budgets for every cell; it is stated, and cells that saturate below it are those listed as small by
the even-reading exhibit). ``exhibit_alpha`` stops at the need or after 3 * need + 1000 draws.
"""

from __future__ import annotations

import json
import math
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

from studies.m0.c1_batch1_capacity import exhibit_alpha
from studies.m0.core import ALL_LEVELS, lineages_of

POOLS = 24_000
TUNING = 100
FACTOR = 10


def demand(g_part: int, level: int, kind: str) -> int:
    if level in (0, 6):
        return TUNING
    share = POOLS / g_part / (5 if kind == "even" else 1)
    return math.ceil(share) + TUNING


def find_lineage(lid: str) -> Any:
    from studies.m0.lineages_c1_common import load_batch1
    from studies.m0.lineages_c1_rev2 import load_rev2

    return next(x for x in [*lineages_of("C1"), *load_batch1(), *load_rev2()] if x.id == lid)


def _cell(args: tuple[str, int, int]) -> tuple[str, int, dict[str, int]]:
    lid, lv, need = args
    distinct, texts, draws = exhibit_alpha(find_lineage(lid), lv, need)
    return lid, lv, {"distinct_up_to_renaming": distinct, "distinct_texts": texts, "draws": draws, "need": need}


def run(g_part: int, out: Path, workers: int = 10) -> dict[str, Any]:
    from studies.m0.lineages_c1_clusters import current_ids

    ids = list(current_ids())
    jobs = [(i, lv, FACTOR * demand(g_part, lv, "even")) for i in ids for lv in ALL_LEVELS]
    rows: dict[str, dict[str, Any]] = {i: {} for i in ids}
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for lid, lv, r in ex.map(_cell, jobs, chunksize=4):
            rows[lid][str(lv)] = r
    short = [(lid, int(lv), c["distinct_up_to_renaming"], c["need"]) for lid, cells in sorted(rows.items()) for lv, c in sorted(cells.items()) if c["distinct_up_to_renaming"] < c["need"]]
    result = {
        "g_part": g_part, "lineages_written": len(ids), "pools_per_part": POOLS, "tuning_per_level": TUNING, "factor": FACTOR,
        "demand_even": {str(lv): demand(g_part, lv, "even") for lv in ALL_LEVELS}, "demand_worst": {str(lv): demand(g_part, lv, "worst") for lv in ALL_LEVELS},
        "need_even": {str(lv): FACTOR * demand(g_part, lv, "even") for lv in ALL_LEVELS}, "need_worst": {str(lv): FACTOR * demand(g_part, lv, "worst") for lv in ALL_LEVELS},
        "cells_total": len(jobs), "cells_below_need_even": len(short), "below_need_even": [{"lineage": a, "level": b, "distinct": c, "need": d} for a, b, c, d in short], "rows": rows,
    }
    out.write_text(json.dumps(result, indent=1, sort_keys=True))
    return result


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--g-part", type=int, default=20)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=10)
    a = ap.parse_args()
    r = run(a.g_part, Path(a.out), a.workers)
    print(json.dumps({k: r[k] for k in ("g_part", "lineages_written", "need_even", "cells_total", "cells_below_need_even")}))
    for x in r["below_need_even"]:
        print(x)


if __name__ == "__main__":
    main()
