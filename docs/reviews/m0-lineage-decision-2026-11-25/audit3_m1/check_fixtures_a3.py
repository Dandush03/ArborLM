# ruff: noqa
"""Audit 3 of M1: my text-only solver on every rev2 fixture item on disk (studies/m0/fixtures/m1_batch1_rev2/*.jsonl), and regeneration of each fixture
file's items is NOT attempted (the writer de-duplicates across levels; the sha256 in the manifest is compared instead)."""
import glob
import hashlib
import json
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from solve_text_a3 import solve

root = sys.argv[1]
man = json.load(open(root + "/studies/m0/manifests/m1_batch1_rev2_manifest.json"))
shas = {r["id"]: r["fixture_sha256"] for r in man["effective_lineages"]}
tot = bad = 0
for f in sorted(glob.glob(root + "/studies/m0/fixtures/m1_batch1_rev2/*.jsonl")):
    lid = f.rsplit("/", 1)[1].removesuffix(".jsonl")
    lines = open(f).read().splitlines()
    sha = hashlib.sha256(open(f, "rb").read()).hexdigest()
    nb = 0
    for ln in lines:
        it = json.loads(ln)
        key, _ = solve(lid, it["question"])
        tot += 1
        if key != it["answer"]:
            nb += 1
    bad += nb
    print(lid, len(lines), "mismatch", nb, "sha matches manifest:", sha == shas.get(lid))
print("total", tot, "mismatches", bad)
