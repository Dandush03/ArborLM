# ruff: noqa
"""Audit 3 (R1): key check with the auditor's text-only solvers, and a determinism digest.

usage (worktree root): PYTHONHASHSEED=<h> uv run --locked python <this> <n_per_level> <seed_base>
Prints per lineage: items checked, mismatches, ambiguous, parse errors (first examples), and a SHA-256 over all
(question, answer) pairs so two runs under different PYTHONHASHSEED can be compared.
"""
import hashlib, os, sys, traceback

sys.path.insert(0, os.path.dirname(__file__))
import gen, solvers3 as S

n = int(sys.argv[1]); base = int(sys.argv[2])
L = gen.lineages()
H = hashlib.sha256()
tot_bad = 0
for lid in sorted(L):
    f = S.SOLVERS.get(lid)
    mism, amb, err, cnt = [], [], [], 0
    for lv in range(7):
        for b in gen.items(L[lid], lv, n, base):
            H.update(b.question.encode()); H.update(b"\x00"); H.update(b.answer.encode()); H.update(b"\x01")
            cnt += 1
            if f is None:
                continue
            try:
                a = f(b.question)
                if a != b.answer:
                    mism.append((lv, a, b.answer, b.question[:300]))
            except S.Ambiguous as e:
                amb.append((lv, str(e), b.answer, b.question[:300]))
            except Exception as e:
                err.append((lv, repr(e)[:120], b.question[:300]))
    tot_bad += len(mism) + len(amb) + len(err)
    print(f"{lid:40s} n={cnt:5d} mismatch={len(mism):4d} ambiguous={len(amb):4d} error={len(err):4d}{'  NO SOLVER' if f is None else ''}")
    for x in (mism[:2] + amb[:2] + err[:2]):
        print("    ", x)
print("digest", H.hexdigest(), "total problems", tot_bad)
