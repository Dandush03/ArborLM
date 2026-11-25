# ruff: noqa: E501
# mypy: disable-error-code="type-arg,no-untyped-call,no-any-return,arg-type,assignment,index,call-overload,var-annotated,list-item,unused-ignore,no-untyped-def"
"""Shortcut measurement of the R1 fix-round-3 set and of the shapes it replaces, per level, two-sided, with the battery of ``r1_fix3_battery`` (the third auditor's battery plus rules for the rebuilt shapes).
Measured, never thresholded. Seeds are throwaway integers given on the command line (not registered study seeds).
Run (worktree root): PYTHONHASHSEED=0 uv run --locked python -m studies.m0.r1_fix3_measure <n_per_level> <seed> <fit_seed> <out.json>
"""

from __future__ import annotations

import json
import sys
from multiprocessing import Pool
from typing import Any

from studies.m0 import r1_fix3_battery as B


def _job(args: tuple[str, str, int, int, int]) -> dict[str, Any]:
    lid, which, n, seed, fit = args
    from studies.m0 import lineages_r1_clusters_v2 as v2
    from studies.m0.lineages_r1_fix3_clusters import registered_v3
    from studies.m0.lineages_r1_fix3_common import load_fix3

    pool = {x.id: x for x in [*registered_v3(), *load_fix3(), *v2.registered_v2()]}
    lin = pool[lid]
    rows = B.measure(lin, n, seed, fit)
    return {"id": lid, "which": which, "summary": B.summarise(rows), "rows": [{k: r[k] for k in ("level", "heuristic", "fired", "acc_fired", "eff", "anti", "chance", "n")} for r in rows]}


def main() -> None:
    from studies.m0 import lineages_r1_clusters_v2 as v2
    from studies.m0.lineages_r1_fix3_clusters import NOT_REGISTERED_V3, registered_v3
    from studies.m0.lineages_r1_fix3_common import REPLACES, load_fix3

    n, seed, fit = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
    out = sys.argv[4]
    new_ids = [x.id for x in registered_v3()]
    attempts = [x.id for x in load_fix3() if x.id in NOT_REGISTERED_V3]  # rebuilds that were not registered
    old_ids = sorted(set(REPLACES.values()) | {i for i in NOT_REGISTERED_V3 if i in {x.id for x in v2.registered_v2()}})
    jobs = [(i, "registered_v3", n, seed, fit) for i in new_ids] + [(i, "not_registered_rebuild", n, seed, fit) for i in attempts] + [(i, "earlier_shape", n, seed, fit) for i in old_ids]
    res = []
    with Pool(12) as p:
        for r in p.imap_unordered(_job, jobs):
            res.append(r)
            print(r["id"], r["which"], flush=True)
    json.dump(sorted(res, key=lambda r: (r["which"], r["id"])), open(out, "w"), indent=1, sort_keys=True)


if __name__ == "__main__":
    main()
