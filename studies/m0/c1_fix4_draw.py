# ruff: noqa: E501
"""C1 fix 4: draw items for the rule scripts (throwaway seeds only; no registered study seed).

Writes one gzip JSONL per lineage, in the format of the auditor's ``audit4_c1/s2_gen.py`` (``{"lid","lv","i","src","key","q","retries","atype"}``), so that the auditor's rule scripts
(``audit4_c1/s4_rules_v2.py``, ``audit3_c1/a3_shortcuts.py``) run on them as they are. The fix-4 lineages (``*_f4``: two with one shape kept, three with repaired levels) are written under the id of their
original (``RULE_ALIAS``): the rule scripts key their shape rules on that name and the program text is the same (a subset of the shapes, or the same shapes with other parameter ranges), so the aliasing changes no rule.

  uv run --locked python -m studies.m0.c1_fix4_draw --per-level 400 --seed 71 --out <dir> [--ids C1.a,C1.b] [--workers 8]

Draw stream: sha256("fix4c1|<seed>|<lineage>|<level>"). Without ``--ids`` the ids are every fix-3 current lineage (the audit's 37) plus the five fix-4 lineages (those files are written under the original's name, so a draw with the default ids has 37 files).
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import random
import sys
import time
from concurrent.futures import ProcessPoolExecutor

# fix-4 id -> the id the auditors' rule scripts know the same program text by (the fix-4 builder draws a subset of the shapes, or the same shapes with distinct levels)
RULE_ALIAS = {
    "C1.sieve_marking_f4": "C1.sieve_marking_f3",
    "C1.fast_power_f4": "C1.fast_power_f3",
    "C1.func_branch_f4": "C1.func_branch",
    "C1.func_compose_f4": "C1.func_compose_f3",
    "C1.slices_f4": "C1.slices",
}


def rng_for(seed: int, lid: str, lv: int) -> random.Random:
    d = hashlib.sha256(f"fix4c1|{seed}|{lid}|{lv}".encode()).digest()
    return random.Random(int.from_bytes(d[:8], "big"))


def audit4_set() -> list[str]:
    """The audit's 37 current lineages (fix-3 state), recomputed from the registries by the audit's rule: every id minus the superseded, the PROPOSED and the NOT REGISTERED ones."""
    from studies.m0.lineages_c1_fix3 import NOT_REGISTERED as NR3
    from studies.m0.lineages_c1_fix3 import SUPERSEDES3, load_fix3
    from studies.m0.lineages_c1_fix4 import all_written
    from studies.m0.lineages_c1_rev2 import PROPOSED
    from studies.m0.lineages_c1_rev2 import SUPERSEDES as SUP2

    load_fix3()
    written = {k: v for k, v in all_written().items() if not k.endswith("_f4")}
    superseded = {*SUPERSEDES3.values(), *SUP2.values()}
    excluded = {k for k in NR3 if "[" not in k}
    return [i for i in sorted(written) if i not in superseded and i not in PROPOSED and i not in excluded]


def draw_rows(lid: str, seed: int, per_level: int) -> list[dict[str, object]]:
    from studies.m0.c1grammar import render
    from studies.m0.core import Retry
    from studies.m0.lineages_c1_fix4 import all_written

    lin = all_written()[lid]
    rows: list[dict[str, object]] = []
    for lv in range(7):
        r = rng_for(seed, lid, lv)
        for i in range(per_level):
            tries = 0
            while True:
                tries += 1
                if tries > 500:
                    raise RuntimeError(f"{lid} L{lv}: 500 retries")
                try:
                    b = lin.build(lv, r)
                    break
                except Retry:
                    continue
            rows.append({"lid": RULE_ALIAS.get(lid, lid), "lv": lv, "i": i, "src": render(b.structured["program"]), "key": b.answer, "q": b.question, "retries": tries - 1, "atype": b.answer_type})
    return rows


def work(args: tuple[str, int, int, str]) -> tuple[str, int, int]:
    lid, seed, per_level, out = args
    rows = draw_rows(lid, seed, per_level)
    name = RULE_ALIAS.get(lid, lid)
    with gzip.open(os.path.join(out, name.replace("C1.", "") + ".jsonl.gz"), "wt") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")
    return lid, len(rows), sum(int(str(r["retries"])) for r in rows)


def main() -> None:
    sys.path.insert(0, ".")
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-level", type=int, default=400)
    ap.add_argument("--seed", type=int, default=71)
    ap.add_argument("--out", required=True)
    ap.add_argument("--ids", default="")
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    ids = a.ids.split(",") if a.ids else [*audit4_set(), *sorted(RULE_ALIAS)]
    with open(os.path.join(a.out, "meta.json"), "w") as f:
        json.dump({"ids": ids, "seed": a.seed, "per_level": a.per_level, "python": sys.version, "rule_alias": RULE_ALIAS}, f, indent=1)
    t = time.time()
    with ProcessPoolExecutor(a.workers) as ex:
        for lid, n, rt in ex.map(work, [(i, a.seed, a.per_level, a.out) for i in ids]):
            print(lid, n, "retries", rt, flush=True)
    print("secs", round(time.time() - t, 1))


if __name__ == "__main__":
    main()
