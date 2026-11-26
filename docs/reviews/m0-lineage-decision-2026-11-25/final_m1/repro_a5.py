# ruff: noqa
"""Final M1 audit: reproducibility. In one process, for every survivor and level: 300 items from core.stream(SEEDS['repro']=2611255, 'final-m1-a5', 'repro', id, level);
prints SHA-256 over the items' Item.to_json() (question, answer, structured, ids), one line per lineage-level, plus a total. Run twice in fresh processes with
different PYTHONHASHSEED and compare the outputs byte for byte (cmp)."""
import hashlib
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from fm1_common import SEEDS, items, survivors

if __name__ == "__main__":
    tot = hashlib.sha256()
    for lid, lin in sorted(survivors().items()):
        for L in range(7):
            h = hashlib.sha256()
            for it in items(lin, L, 300, SEEDS["repro"], "repro"):
                h.update(it.to_json().encode("utf-8") + b"\n")
            tot.update(h.digest())
            print(lid, L, h.hexdigest())
    print("TOTAL", tot.hexdigest())
