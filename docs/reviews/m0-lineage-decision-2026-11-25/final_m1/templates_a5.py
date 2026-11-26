# ruff: noqa
"""Final M1 audit: list the distinct text templates per surviving lineage (digits -> #, capitalised words -> W, the setting sentence removed),
so the text solver can be written from the item texts. 300 items per level, seed SEEDS['samples'] label 'tmpl'."""
import re
import sys
from collections import Counter

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from fm1_common import SEEDS, items, survivors

CTX = [r"^\S+ from \S+ found this problem in a puzzle book\. ", r"^This problem comes from a quiz held in \S+, set by \S+\. ", r"^\S+ of \S+ wrote this problem for a maths club\. ", r"^At a maths club in \S+, \S+ is asked this\. "]


def tmpl(q):
    for c in CTX:
        q = re.sub(c, "", q)
    q = re.sub(r"\d+(\.\d+)?", "#", q)
    q = re.sub(r"\b[A-Z][a-z]+\b", "W", q)
    q = re.sub(r"(#(, #)+)", "#LIST", q)
    return q


if __name__ == "__main__":
    reg = survivors()
    for lid, lin in sorted(reg.items()):
        c = Counter()
        ex = {}
        for L in range(7):
            for it in items(lin, L, 300, SEEDS["samples"], "tmpl"):
                t = tmpl(it.question)
                c[t] += 1
                ex.setdefault(t, (L, it.question, it.answer))
        print(f"##### {lid}: {len(c)} templates")
        for t, k in c.most_common(12):
            L, q, a = ex[t]
            print(f"  [{k}] {t}\n      e.g. L{L} ans={a}: {q}")
