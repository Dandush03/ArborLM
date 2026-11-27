# ruff: noqa
# ruff: noqa
"""Print sampled items: python show.py <samples dir> <per-level k> <maxchars> <lineage ids...>"""
import json
import os
import sys

d, k, mx = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
for lid in sys.argv[4:]:
    rows = [json.loads(x) for x in open(os.path.join(d, lid + ".jsonl"))]
    print(f"===== {lid}")
    seen = {}
    for x in rows:
        c = seen.get(x["level"], 0)
        if c >= k:
            continue
        seen[x["level"]] = c + 1
        q = x["question"]
        if len(q) > mx:
            q = q[: mx // 2] + " [...] " + q[-mx // 2 :]
        print(f"[{x['id']}] L{x['level']} ANS={x['answer']!r}\n  {q}")
