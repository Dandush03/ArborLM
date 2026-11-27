# ruff: noqa
"""Final M1 audit: compare the text solver (solve_text_a5) with the stored key, N items per lineage and level at a fresh seed.
Usage (from the implementation worktree): PYTHONHASHSEED=h PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 uv run --locked --offline python check_keys_a5.py N SEED out.json"""
import json
import sys
from collections import defaultdict
from fractions import Fraction as F
from multiprocessing import get_context

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from fm1_common import items, stem, survivors
from solve_text_a5 import solve


def run(args):
    lid, N, seed = args
    lin = survivors()[lid]
    st = stem(lid)
    out = {}
    for L in range(7):
        mm, err, amb, ex_mm, ex_amb, ex_err = 0, 0, 0, [], [], []
        issues = defaultdict(int)
        for it in items(lin, L, N, seed, "keys"):
            try:
                v, iss = solve(st, it.question)
            except Exception as e:
                err += 1
                if len(ex_err) < 3:
                    ex_err.append([repr(e)[:200], it.question, it.answer])
                continue
            if iss:
                amb += 1
                for i in iss:
                    issues[i.split(",")[0][:60]] += 1
                if len(ex_amb) < 3:
                    ex_amb.append([iss, it.question, it.answer])
            if v != F(it.answer):
                mm += 1
                if len(ex_mm) < 5:
                    ex_mm.append([str(v), it.answer, it.question])
        out[str(L)] = {"N": N, "mismatch": mm, "solver_error": err, "no_unique_answer": amb, "issues": dict(issues), "ex_mismatch": ex_mm, "ex_ambiguous": ex_amb, "ex_error": ex_err}
    return lid, out


if __name__ == "__main__":
    N, seed, path = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
    only = sys.argv[4].split(",") if len(sys.argv) > 4 else None
    ids = sorted(survivors())
    if only:
        ids = [i for i in ids if any(o in i for o in only)]
    with get_context("spawn").Pool(12) as p:
        res = dict(p.map(run, [(i, N, seed) for i in ids], chunksize=1))
    json.dump({"N": N, "seed": seed, "results": res}, open(path, "w"), indent=1, sort_keys=True)
    tot_n = tot_mm = tot_err = tot_amb = 0
    for lid in ids:
        r = res[lid]
        mm = [r[str(L)]["mismatch"] for L in range(7)]
        er = [r[str(L)]["solver_error"] for L in range(7)]
        am = [r[str(L)]["no_unique_answer"] for L in range(7)]
        tot_n += 7 * N; tot_mm += sum(mm); tot_err += sum(er); tot_amb += sum(am)
        print(f"{lid}: mismatch {sum(mm)}/{7*N} per level {mm}; solver errors {sum(er)}; no unique answer {sum(am)} per level {am}", flush=True)
        for L in range(7):
            x = r[str(L)]
            for e in x["ex_mismatch"][:2]:
                print(f"   MISMATCH L{L}: solver {e[0]} key {e[1]} :: {e[2][:400]}")
            for e in x["ex_error"][:1]:
                print(f"   ERROR L{L}: {e[0]} :: {e[1][:300]}")
            for e in x["ex_ambiguous"][:1]:
                print(f"   NO-UNIQUE L{L}: {e[0]} key {e[2]} :: {e[1][:300]}")
    print(f"TOTAL items {tot_n}, mismatches {tot_mm}, solver errors {tot_err}, no unique answer {tot_amb}")
