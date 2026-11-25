# ruff: noqa
"""Print items. Usage: show.py ITEMSDIR LID MODE LEVEL K [MAXCHARS]  or  show.py ITEMSDIR --counts"""
import gzip, json, os, sys
from collections import Counter

d = sys.argv[1]
if sys.argv[2] == "--counts":
    for f in sorted(os.listdir(d)):
        rows = [json.loads(x) for x in gzip.open(os.path.join(d, f), "rt")]
        lv = Counter(r["level"] for r in rows)
        uq = len({r["q"] for r in rows})
        print(f, len(rows), dict(sorted(lv.items())), "unique", uq)
    sys.exit()
lid, mode, level, k = sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5])
mx = int(sys.argv[6]) if len(sys.argv) > 6 else 100000
rows = [json.loads(x) for x in gzip.open(os.path.join(d, f"{lid}.{mode}.jsonl.gz"), "rt")]
for r in [r for r in rows if r["level"] == level][:k]:
    q = r["q"] if len(r["q"]) <= mx else r["q"][: mx // 2] + " [...] " + r["q"][-mx // 2:]
    print(r["id"], "| key:", r["a"], "| k:", r["k"])
    print("  ", q)
