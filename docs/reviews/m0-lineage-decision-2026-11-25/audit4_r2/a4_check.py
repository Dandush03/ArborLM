# ruff: noqa
"""Audit 4 (R2): key check with my TEXT-ONLY solvers (a4_solvers, which see only it.question) + a generation hash for determinism.
Seeds: random.Random(f"a4r2|{lid}|{level}|{K}") (string seed; throwaway, NOT a registered study seed).
Usage (cwd = audited worktree): PYTHONHASHSEED=<h> PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:<deliver> uv run --locked --offline python a4_check.py N K"""
import hashlib
import json
import random
import sys
from multiprocessing import Pool

N = int(sys.argv[1])
K = sys.argv[2]


def one(lid):
    from studies.m0.core import ALL_LEVELS, build_item
    from studies.m0.r2_fix3_set import fix3_set
    import a4_solvers as S

    lin = fix3_set()[lid]
    sol = S.SOLVERS[lid.split(".", 1)[1]]
    h = hashlib.sha256()
    rows = []
    for lv in ALL_LEVELS:
        r = random.Random(f"a4r2|{lid}|{lv}|{K}")
        bad = err = 0
        ex = []
        for i in range(N):
            it = build_item(lin, lv, r, "A", f"{lid}/{lv}/{i}")
            h.update(json.dumps([it.question, it.structured, it.answer, it.answer_type, it.k], sort_keys=True).encode())
            try:
                a = sol(it.question)
            except Exception as e:
                err += 1
                if len(ex) < 2:
                    ex.append(("ERROR", repr(e), it.question[:300]))
                continue
            if a != it.answer:
                bad += 1
                if len(ex) < 3:
                    ex.append(("MISMATCH", a, it.answer, it.question[:400]))
        rows.append((lv, bad, err, ex))
    return lid, h.hexdigest(), rows


if __name__ == "__main__":
    sys.path.insert(0, ".")
    from studies.m0.r2_fix3_set import fix3_set

    ids = sorted(fix3_set())
    with Pool(12) as p:
        res = p.map(one, ids)
    tot = bad = err = 0
    H = hashlib.sha256()
    for lid, hx, rows in res:
        H.update(hx.encode())
        for lv, b, e, ex in rows:
            tot += N
            bad += b
            err += e
            print(f"{lid} L{lv}: n={N} mismatches={b} errors={e}")
            for x in ex:
                print("   ", x)
    print(f"lineages={len(ids)} TOTAL items={tot} mismatches={bad} errors={err}")
    print("generation sha256", H.hexdigest())
