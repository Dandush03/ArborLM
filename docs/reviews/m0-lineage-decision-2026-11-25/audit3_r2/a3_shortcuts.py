# ruff: noqa
"""Audit 3 (R2): shortcut measurement. Per lineage, level and shape: accuracy of each heuristic in a3_heur.py and of the most frequent answer
(mode learned on a separate training draw). Two-sided for yes/no: |acc - 0.5|. Open answers: chance 0 (ADR-0033 section 7, 'chance level').
Seeds: training draw random.Random(f"a3r2|{lid}|{lv}|5"), test draw random.Random(f"a3r2|{lid}|{lv}|6").
Usage: ... python a3_shortcuts.py N OUT.json"""
import json
import math
import random
import sys
from collections import Counter
from multiprocessing import Pool

N = int(sys.argv[1])
OUT = sys.argv[2]


def shape(lid, s):
    for k in ("ask", "convention", "kind"):
        if k in s and isinstance(s[k], str):
            v = s[k]
            if lid.endswith("cache_eviction"):
                v = s["policy"] + "/" + v
            return v
    if lid.endswith("min_heap_ops"):
        return f"removals={s['removals']}"
    return "-"


def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    w = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (c - w, c + w)


def run(lid):
    from studies.m0.core import ALL_LEVELS, build_item
    from a3_set import current
    import a3_heur as HH
    lin = current()[lid]
    name = lid.split(".", 1)[1]
    hs = HH.H.get(name, [])
    res = {}
    for lv in ALL_LEVELS:
        rtr = random.Random(f"a3r2|{lid}|{lv}|5")
        rte = random.Random(f"a3r2|{lid}|{lv}|6")
        tr = [build_item(lin, lv, rtr, "A", "t") for _ in range(N)]
        te = [build_item(lin, lv, rte, "A", "e") for _ in range(N)]
        modes = {}
        for sh, grp in _group(lid, tr).items():
            modes[sh] = Counter(it.answer for it in grp).most_common(1)[0][0]
        modes_all = Counter(it.answer for it in tr).most_common(1)[0][0]
        rows = {}
        for sh, grp in _group(lid, te).items():
            at = grp[0].answer_type
            k = grp[0].k
            chance = 0.5 if at == "yn" else (1 / k if k else 0.0)
            ent = {"n": len(grp), "answer_type": at, "chance": chance, "heur": {}}
            if at == "yn":
                ent["yes_share"] = sum(it.answer == "yes" for it in grp) / len(grp)
            # mode
            m = modes.get(sh)
            c = sum(it.answer == m for it in grp) if m is not None else 0
            ent["heur"]["most frequent answer (train draw)"] = {"n": len(grp), "k": c, "acc": c / len(grp), "value": m}
            # distinct answers
            ent["distinct_answers"] = len({it.answer for it in grp})
            for hn, fn in hs:
                kk = nn = 0
                for it in grp:
                    try:
                        a = fn(it.structured, it.question)
                    except Exception as e:  # a heuristic failing is recorded, not hidden
                        a = None
                        ent.setdefault("heur_errors", Counter())[hn] += 1
                    if a is None:
                        continue
                    nn += 1
                    kk += a == it.answer
                if nn:
                    ent["heur"][hn] = {"n": nn, "k": kk, "acc": kk / nn}
            for hn, v in ent["heur"].items():
                v["lo"], v["hi"] = wilson(v["k"], v["n"])
                v["minus_chance"] = v["acc"] - chance
                if at == "yn":
                    v["two_sided"] = abs(v["acc"] - 0.5)
            if "heur_errors" in ent:
                ent["heur_errors"] = dict(ent["heur_errors"])
            rows[sh] = ent
        res[str(lv)] = rows
    return lid, res


def _group(lid, items):
    g = {}
    for it in items:
        g.setdefault(shape(lid, it.structured), []).append(it)
    return g


if __name__ == "__main__":
    from a3_set import current
    ids = list(current())
    if len(sys.argv) > 3:
        ids = [i for i in ids if i in sys.argv[3].split(",")]
    with Pool(12) as p:
        out = dict(p.map(run, ids))
    json.dump({"N": N, "lineages": out}, open(OUT, "w"), indent=1, sort_keys=True)
    print("wrote", OUT)
