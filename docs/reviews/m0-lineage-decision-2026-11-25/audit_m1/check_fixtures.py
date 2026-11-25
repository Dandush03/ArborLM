# ruff: noqa
"""Check every fixture item of the 21 M1 batch-1 lineages against the auditor's independent solvers (question text only).

Run (from anywhere; imports only this folder):
  PYTHONDONTWRITEBYTECODE=1 uv run --locked --offline python check_fixtures.py <fixtures_dir> > fixture_check.txt
"""
import json
import re
import sys
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_solvers import solve  # noqa: E402

fx = Path(sys.argv[1])
tot = agree = 0
wrong = []
errors = []
alts = defaultdict(list)
stated = Counter()
per_lin = Counter()
for f in sorted(fx.glob("M1.*.jsonl")):
    for line in f.read_text().splitlines():
        it = json.loads(line)
        lid = it["lineage"]
        tot += 1
        per_lin[lid] += 1
        try:
            res = solve(lid, it["question"])
        except Exception as e:  # keep every failure
            errors.append((it["id"], repr(e)))
            continue
        if res["answer"] == it["answer"]:
            agree += 1
        else:
            wrong.append((it["id"], it["answer"], res["answer"], it["question"]))
        for k, v in (res.get("alt") or {}).items():
            if v != it["answer"]:
                alts[(lid, k)].append((it["id"], it["answer"], v))
        nums = set(re.findall(r"\b\d+(?:\.\d+)?\b", re.sub(r"\d-digit", "", it["question"])))
        if it["answer"] in nums:
            stated[lid] += 1
print(f"fixture items: {tot}; solver agrees with key: {agree}; disagreements: {len(wrong)}; solver errors: {len(errors)}")
for w in wrong:
    print("WRONG/DISAGREE", w)
for e in errors:
    print("ERROR", e)
print("\nAlternative readings that change the key (count of fixture items, first 3 ids):")
for (lid, k), xs in sorted(alts.items()):
    print(f"  {lid} [{k}] {len(xs)}/{per_lin[lid]}  e.g. {xs[:3]}")
print("\nKey appears verbatim among the numbers printed in the question (count / items):")
for lid in sorted(per_lin):
    print(f"  {lid:30s} {stated[lid]:3d}/{per_lin[lid]}")
