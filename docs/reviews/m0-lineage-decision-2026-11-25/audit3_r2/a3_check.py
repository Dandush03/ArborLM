# ruff: noqa
"""Audit 3 (R2): key correctness with my own solvers + a determinism hash.
Seeds: random.Random(f"a3r2|{lid}|{level}|{k}") with k = 1 (string seed, hashed by SHA-512 inside random; independent of PYTHONHASHSEED). Not a registered seed.
Usage (from the audited worktree): PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:<this dir> uv run --locked --offline python a3_check.py N K > out"""
import hashlib
import json
import random
import sys

from studies.m0.core import ALL_LEVELS, build_item
from a3_set import current
import a3_solvers as S

N = int(sys.argv[1]) if len(sys.argv) > 1 else 400
K = int(sys.argv[2]) if len(sys.argv) > 2 else 1


def main():
    cur = current()
    tot = bad = err = 0
    h = hashlib.sha256()
    for lid, lin in cur.items():
        name = lid.split(".", 1)[1]
        sol = S.SOLVERS[name]
        for lv in ALL_LEVELS:
            r = random.Random(f"a3r2|{lid}|{lv}|{K}")
            nb = ne = 0
            for i in range(N):
                it = build_item(lin, lv, r, "A", f"{lid}/{lv}/{i}")
                h.update(json.dumps([it.question, it.structured, it.answer], sort_keys=True).encode())
                tot += 1
                try:
                    a = sol(it.structured, it.question)
                except Exception as e:
                    ne += 1
                    if ne <= 2:
                        print("ERROR", lid, lv, i, repr(e), json.dumps(it.structured)[:300])
                    continue
                if a != it.answer:
                    nb += 1
                    if nb <= 3:
                        print("MISMATCH", lid, lv, i, "mine", a, "key", it.answer, json.dumps(it.structured)[:400])
            bad += nb
            err += ne
            print(f"{lid} L{lv}: n={N} mismatches={nb} errors={ne}", flush=True)
    print(f"TOTAL items={tot} mismatches={bad} errors={err}")
    print("generation sha256", h.hexdigest())


main()
