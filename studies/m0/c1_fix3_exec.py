# ruff: noqa: E501
"""Execute the rendered program of every drawn item of the fix round 3 lineages in FRESH subprocesses under more than one interpreter and hash seed (brief item 4).

For each lineage and level, ``--per-level`` items are drawn (throwaway seed); every program is run by the isolated runner of ``c1grammar`` (``python -I -S``, a per-program 2 s alarm, a 600 s
process timeout) once per (interpreter, PYTHONHASHSEED) pair given; the printed line must be exactly one line and equal the builder's key (which the locked interpreter produced in process).
The result is printed and returned: items, errors, key mismatches, disagreements between runs, outputs that are not one line.

  uv run --locked python -m studies.m0.c1_fix3_exec --per-level 300 --seed 5 [--interpreters <py>,<py2>] [--hash-seeds 0,98765] [--only id,..]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from typing import Any

from studies.m0.c1grammar import _RUNNER


def run_fresh(sources: list[str], interpreter: str, hash_seed: str, timeout_s: float = 600.0) -> list[dict[str, Any]]:
    proc = subprocess.run([interpreter, "-I", "-S", "-c", _RUNNER], input=json.dumps(sources), capture_output=True, text=True, timeout=timeout_s, check=False, env={"PYTHONHASHSEED": hash_seed})
    if proc.returncode != 0:
        raise RuntimeError(f"runner failed under {interpreter} seed {hash_seed}: {proc.stderr[-300:]}")
    out: list[dict[str, Any]] = json.loads(proc.stdout)
    return out


def check(per_level: int, seed: int, interpreters: list[str], hash_seeds: list[str], only: list[str]) -> dict[str, Any]:
    from studies.m0.c1_fix3_battery import draw
    from studies.m0.lineages_c1_fix3 import load_fix3

    ids = [x.id for x in load_fix3()]
    if only:
        ids = [i for i in ids if i in only]
    report: dict[str, Any] = {"interpreters": interpreters, "hash_seeds": hash_seeds, "per_level": per_level, "seed": seed, "lineages": {}}
    total = {"items": 0, "errors": 0, "key_mismatches": 0, "run_disagreements": 0, "not_one_line": 0}
    for lid in ids:
        rows = draw(lid, seed, per_level)
        srcs = [r["src"] for r in rows]
        runs = [run_fresh(srcs, py, hs) for py in interpreters for hs in hash_seeds]
        c = {"items": len(rows), "errors": 0, "key_mismatches": 0, "run_disagreements": 0, "not_one_line": 0}
        for k, row in enumerate(rows):
            outs = [rr[k] for rr in runs]
            if any(o["err"] is not None and o["out"] is None and "not exactly one line" in (o["err"] or "") for o in outs):
                c["not_one_line"] += 1
            if any(o["err"] is not None for o in outs):
                c["errors"] += 1
                continue
            if len({o["out"] for o in outs}) > 1:
                c["run_disagreements"] += 1
            if outs[0]["out"] != row["key"]:
                c["key_mismatches"] += 1
        report["lineages"][lid] = c
        for kk in total:
            total[kk] += c[kk]
        print(lid, c, flush=True)
    report["total"] = total
    return report


def main() -> None:
    sys.path.insert(0, ".")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--per-level", type=int, default=300)
    ap.add_argument("--seed", type=int, default=5)
    ap.add_argument("--interpreters", default=sys.executable)
    ap.add_argument("--hash-seeds", default="0,98765")
    ap.add_argument("--only", default="")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    rep = check(a.per_level, a.seed, a.interpreters.split(","), a.hash_seeds.split(","), [x for x in a.only.split(",") if x])
    print("TOTAL", rep["total"])
    if a.out:
        with open(a.out, "w") as f:
            json.dump(rep, f, indent=1, sort_keys=True)


if __name__ == "__main__":
    main()
