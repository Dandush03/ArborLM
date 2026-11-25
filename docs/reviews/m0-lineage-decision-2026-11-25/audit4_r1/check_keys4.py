# ruff: noqa
"""Audit 4 (R1): key check with the auditors' text-only solvers, and a determinism digest.

usage (implementation worktree root): PYTHONHASHSEED=<h> uv run --locked python <this> <n_per_level> <seed_base> [substr]
Primary solver: solvers4 (this audit) for every _r5 shape; solvers3 (audit 3, reused unchanged) for the ten kept shapes.
Secondary: solvers3 on the _r5 shapes whose text it still parses. Prints per lineage: items, mismatches, ambiguous, errors,
retries (Retry raised by the builder), and a SHA-256 over all (question, answer) pairs to compare two hash seeds.
"""
import hashlib, os, re, sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import gen4, solvers4 as S4, solvers3 as S3

n = int(sys.argv[1]); base = int(sys.argv[2]); filt = sys.argv[3] if len(sys.argv) > 3 else ""
L = gen4.lineages()
H = hashlib.sha256()
tot_bad = 0
OLDMAP = {lid: next((k for k in S3.SOLVERS if re.sub(r"_r\d$", "", k) == re.sub(r"_r\d$", "", lid)), None) for lid in L}
for lid in sorted(L):
    if filt and filt not in lid:
        continue
    prim = S4.SOLVERS.get(lid) or (S3.SOLVERS.get(lid) if not lid.endswith("_r5") else None)
    sec = S3.SOLVERS.get(OLDMAP[lid]) if lid.endswith("_r5") and OLDMAP[lid] else None
    mism, amb, err, sbad, scnt, cnt, rtot = [], [], [], [], 0, 0, 0
    for lv in range(7):
        its, rt = gen4.items(L[lid], lv, n, base, count_retries=True)
        rtot += rt
        for b in its:
            H.update(b.question.encode()); H.update(b"\x00"); H.update(b.answer.encode()); H.update(b"\x01")
            cnt += 1
            try:
                a = prim(b.question)
                if a != b.answer:
                    mism.append((lv, a, b.answer, b.question[:300]))
            except (S4.Ambiguous, S3.Ambiguous) as e:
                amb.append((lv, str(e), b.answer, b.question[:300]))
            except Exception as e:
                err.append((lv, repr(e)[:120], b.question[:300]))
            if sec is not None:
                try:
                    a2 = sec(b.question)
                    scnt += 1
                    if a2 != b.answer:
                        sbad.append((lv, a2, b.answer))
                except Exception as e:
                    sbad.append((lv, "ERR " + repr(e)[:80], b.answer))
    tot_bad += len(mism) + len(amb) + len(err)
    sec_txt = f" second({OLDMAP[lid]})={scnt - len([x for x in sbad if not str(x[1]).startswith('ERR')])}/{cnt} bad={len(sbad)}" if sec else ""
    print(f"{lid:38s} n={cnt:5d} retries={rtot:6d} mismatch={len(mism):3d} ambiguous={len(amb):3d} error={len(err):3d}{sec_txt}", flush=True)
    for x in (mism[:2] + amb[:2] + err[:2] + sbad[:2]):
        print("    ", x)
print("digest", H.hexdigest(), "total problems", tot_bad)
