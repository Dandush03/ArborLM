# ruff: noqa
"""Final M1 audit: distinct question sentences and distinct masked sentences per lineage (digits -> #, capitalised names -> W), 400 items per level, seed SEEDS['samples'] label 'asks'.
Used only to learn the item wording before writing the text solver."""
import re
import sys
from collections import Counter

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from fm1_common import SEEDS, items, survivors

if __name__ == "__main__":
    reg = survivors()
    only = sys.argv[1].split(",") if len(sys.argv) > 1 else None
    for lid, lin in sorted(reg.items()):
        if only and not any(o in lid for o in only):
            continue
        c = Counter()
        for L in range(7):
            for it in items(lin, L, 400, SEEDS["samples"], "asks"):
                q = re.sub(r"\d+(\.\d+)?", "#", it.question)
                q = re.sub(r"\b[A-Z][a-z]+\b", "W", q)
                for s in re.split(r"(?<=[.?;:])\s+", q):
                    c[s] += 1
        print(f"##### {lid}: {len(c)} masked sentences")
        for s, k in sorted(c.items()):
            if k >= 1:
                print(f"  [{k}] {s[:220]}")
