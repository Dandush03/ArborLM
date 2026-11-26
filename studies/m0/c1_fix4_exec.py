# ruff: noqa: E501
"""C1 fix 4: re-check the answer keys of the surviving lineages by EXECUTING the programs.

For each lineage and level, ``--per-level`` items are built (throwaway seed, stream sha256("fix4c1-exec|seed|lineage|level")). The key the builder wrote (what the locked interpreter printed in process) is
compared with (a) the output of the same program run in a FRESH subprocess by the isolated runner of ``c1grammar`` (``python -I -S``, a 2 s alarm per program) under every (interpreter, PYTHONHASHSEED) pair
given, and (b) the independent tree-walking second solver ``solvers_c1.c1_trace`` on the structured program. Counts: items, errors, key mismatches, disagreements between runs, outputs that are not exactly one line,
second-solver mismatches. The two interpreters must be given by path; this module does not look for them.

  uv run --locked python -m studies.m0.c1_fix4_exec --per-level 150 --seed 5 --interpreters <py>,<py2> --hash-seeds 0,98765 --ids <comma list> --out <json>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from typing import Any


def build_rows(lid: str, seed: int, per_level: int) -> list[dict[str, Any]]:
    from studies.m0.c1grammar import render
    from studies.m0.core import Retry
    from studies.m0.lineages_c1_fix4 import all_written

    lin = all_written()[lid]
    rows: list[dict[str, Any]] = []
    for lv in range(7):
        d = hashlib.sha256(f"fix4c1-exec|{seed}|{lid}|{lv}".encode()).digest()
        r = random.Random(int.from_bytes(d[:8], "big"))
        for _ in range(per_level):
            for _try in range(500):
                try:
                    b = lin.build(lv, r)
                    break
                except Retry:
                    continue
            else:
                raise RuntimeError(f"{lid} L{lv}: 500 retries")
            rows.append({"lv": lv, "src": render(b.structured["program"]), "key": b.answer, "structured": b.structured})
    return rows


def check(ids: list[str], per_level: int, seed: int, interpreters: list[str], hash_seeds: list[str]) -> dict[str, Any]:
    from studies.m0.c1_fix3_exec import run_fresh
    from studies.m0.solvers_c1 import c1_trace

    report: dict[str, Any] = {"interpreters": interpreters, "hash_seeds": hash_seeds, "per_level": per_level, "seed": seed, "lineages": {}}
    total = {"items": 0, "errors": 0, "key_mismatches": 0, "run_disagreements": 0, "not_one_line": 0, "second_solver_mismatches": 0}
    for lid in ids:
        rows = build_rows(lid, seed, per_level)
        srcs = [r["src"] for r in rows]
        runs = [run_fresh(srcs, py, hs) for py in interpreters for hs in hash_seeds]
        c = {"items": len(rows), "errors": 0, "key_mismatches": 0, "run_disagreements": 0, "not_one_line": 0, "second_solver_mismatches": 0}
        for k, row in enumerate(rows):
            outs = [rr[k] for rr in runs]
            if any(o["err"] is not None and "not exactly one line" in (o["err"] or "") for o in outs):
                c["not_one_line"] += 1
            if any(o["err"] is not None for o in outs):
                c["errors"] += 1
            else:
                if len({o["out"] for o in outs}) > 1:
                    c["run_disagreements"] += 1
                if outs[0]["out"] != row["key"]:
                    c["key_mismatches"] += 1
            try:
                if c1_trace(row["structured"]) != row["key"]:
                    c["second_solver_mismatches"] += 1
            except Exception:
                c["second_solver_mismatches"] += 1
        report["lineages"][lid] = c
        for kk in total:
            total[kk] += c[kk]
        print(lid, c, flush=True)
    report["total"] = total
    return report


def main() -> None:
    sys.path.insert(0, ".")
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-level", type=int, default=150)
    ap.add_argument("--seed", type=int, default=5)
    ap.add_argument("--interpreters", default=sys.executable)
    ap.add_argument("--hash-seeds", default="0,98765")
    ap.add_argument("--ids", required=True)
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    rep = check(a.ids.split(","), a.per_level, a.seed, a.interpreters.split(","), a.hash_seeds.split(","))
    print("TOTAL", rep["total"])
    if a.out:
        with open(a.out, "w") as f:
            json.dump(rep, f, indent=1, sort_keys=True)


if __name__ == "__main__":
    main()
