# ruff: noqa
"""Run the auditor's question-only solvers over all 140 fixture items of each of the 26 lineages; report every
disagreement and every solver error by item id. Pure stdlib; does not import the generators."""
import json
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from solvers import SOLVERS

FIX = sys.argv[1]
names = sorted(f for f in os.listdir(FIX) if f.endswith(".jsonl"))
print(f"solvers={len(SOLVERS)} fixture files={len(names)}")
tot = bad = err = 0
for f in names:
    lid = f[:-6]
    fn = SOLVERS.get(lid)
    if fn is None:
        print(f"NO SOLVER for {lid}")
        continue
    n_ok = n_bad = n_err = 0
    for line in open(os.path.join(FIX, f)):
        it = json.loads(line)
        tot += 1
        try:
            got = fn(it["question"])
        except Exception as e:
            n_err += 1
            err += 1
            print(f"  ERROR {it['id']}: {type(e).__name__}: {e}")
            continue
        if got.strip().lower() != it["answer"].strip().lower():
            n_bad += 1
            bad += 1
            print(f"  DISAGREE {it['id']}: key={it['answer']!r} auditor={got!r}")
        else:
            n_ok += 1
    print(f"{lid}: agree={n_ok} disagree={n_bad} error={n_err}")
print(f"TOTAL items={tot} disagree={bad} error={err}")
