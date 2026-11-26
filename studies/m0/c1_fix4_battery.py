# ruff: noqa: E501
"""C1 fix 4: the fix-3 battery (``c1_fix3_battery``) re-run on the fix-4 lineage set (the implementer's rules, unchanged; this module only adds the two one-shape lineages).

``c1_fix3_battery.evaluate`` draws from ``all_lineages()`` and applies its shape rules by the id's fix-3 name. The fix-4 lineages (``RULE_ALIAS``) are therefore
measured under their original names: in the worker processes ``all_lineages()`` is patched so that those names build with the fix-4 builders (the battery's rules for
those names are the same; the dropped shapes simply never occur). The output carries the fix-4 names. Note: the battery's shape rules are keyed on ids ending ``_f3``, so for
``C1.func_branch`` and ``C1.slices`` (older ids) it applies its generic rules only.

  uv run --locked python -m studies.m0.c1_fix4_battery --per-level 400 --seed 83 --out <json> [--only ids] [--workers 8]
"""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from typing import Any

from studies.m0.c1_fix4_draw import RULE_ALIAS  # noqa: E402

SWAP = {v: k for k, v in RULE_ALIAS.items()}  # the fix-3 / older id the battery knows -> the fix-4 id


def _patch() -> None:
    from studies.m0 import c1_fix3_battery as bat
    from studies.m0.lineages_c1_fix4 import all_written

    written = all_written()
    orig = bat.all_lineages

    def patched() -> dict[str, Any]:
        d = dict(orig())
        for f3_id, f4_id in SWAP.items():
            d[f3_id] = written[f4_id]
        return d

    bat.all_lineages = patched


def evaluate(args: tuple[str, int, int]) -> tuple[str, dict[str, Any]]:
    from studies.m0 import c1_fix3_battery as bat

    _patch()
    return bat.evaluate(args)


def main() -> None:
    sys.path.insert(0, ".")
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-level", type=int, default=400)
    ap.add_argument("--seed", type=int, default=83)
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", default="")
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    from studies.m0.c1_fix3_battery import summarise
    from studies.m0.c1_fix4_draw import audit4_set

    ids = a.only.split(",") if a.only else audit4_set()
    res: dict[str, Any] = {}
    with ProcessPoolExecutor(a.workers) as ex:
        for lid, per in ex.map(evaluate, [(i, a.seed, a.per_level) for i in ids]):
            out_id = SWAP.get(lid, lid)
            res[out_id] = per
            print(out_id, "done", flush=True)
    with open(a.out, "w") as f:
        json.dump(res, f, indent=1, sort_keys=True)
    print(summarise(res))


if __name__ == "__main__":
    main()
