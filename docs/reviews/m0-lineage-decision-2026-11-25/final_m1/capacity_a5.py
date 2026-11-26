# ruff: noqa
"""Final M1 audit: capacity sampling. M draws per lineage and level from core.stream(SEEDS['capacity']=2611254, 'final-m1-a5', 'cap', id, level).
Two keys: TEXT = core.text_hash(question) (the normalisation draw_items de-duplicates on: NFKC, case-fold, whitespace; names and setting included);
STRUCT = json of the structured form with sorted keys (my own key: names, setting and object words are not in it; the ORDER of listed parts is kept, so it is
less strict than the audit-4 canonical key for commutative parts); A4KEY = audit 4's canonical structural key (capacity_a4.key, read unchanged with importlib)
applied to the same items (the key the implementer's list of eight was computed with). Version 2: A4KEY added after the first run (capacity_M30000.json, text and
struct only; the same items, so its text/struct numbers are unchanged). Per key: distinct D, colliding pairs P, singletons f1, doubletons f2.
n_eff = M(M-1)/(2P); with P = 0 the 95 % lower bound M(M-1)/6 is used (as audit 4 and the implementer). Chao1 = D + f1^2/(2 f2)."""
import json
import sys
from collections import Counter
from multiprocessing import get_context

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from fm1_common import SEEDS, items, survivors
from studies.m0.core import text_hash


def stats(cnt, M):
    P = sum(c * (c - 1) // 2 for c in cnt.values())
    f1 = sum(1 for c in cnt.values() if c == 1)
    f2 = sum(1 for c in cnt.values() if c == 2)
    return {"D": len(cnt), "P": P, "f1": f1, "f2": f2, "n_eff": M * (M - 1) / (2 * P) if P else M * (M - 1) / 6, "no_collision": P == 0,
            "chao1": len(cnt) + (f1 * f1 / (2 * f2) if f2 else f1 * (f1 - 1) / 2)}


def a4key():
    import importlib.util
    from pathlib import Path
    pth = Path("docs/reviews/m0-lineage-decision-2026-11-25/audit4_m1/capacity_a4.py").resolve()
    sys.path.insert(0, str(pth.parent))
    spec = importlib.util.spec_from_file_location("capacity_a4_final", str(pth))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.key


def one(args):
    lid, L, M = args
    k4 = a4key()
    from fm1_common import stem
    lin = survivors()[lid]
    its = items(lin, L, M, SEEDS["capacity"], "cap")
    t = Counter(text_hash(it.question) for it in its)
    s = Counter(json.dumps(it.structured, sort_keys=True) for it in its)
    a = Counter(k4(stem(lid), it.structured) for it in its)
    return lid, L, {"M": M, "text": stats(t, M), "struct": stats(s, M), "a4key": stats(a, M)}


if __name__ == "__main__":
    M, path = int(sys.argv[1]), sys.argv[2]
    ids = sorted(survivors())
    res = {}
    with get_context("spawn").Pool(14) as p:
        for lid, L, r in p.imap_unordered(one, [(i, L, M) for i in ids for L in range(7)], chunksize=1):
            res.setdefault(lid, {})[str(L)] = r
    json.dump({"M": M, "seed": SEEDS["capacity"], "results": res}, open(path, "w"), indent=1, sort_keys=True)
    print("done", len(res))
