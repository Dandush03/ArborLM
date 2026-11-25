# ruff: noqa
"""Audit 4 (R1): did the rebuild create the rule? Forward chaining (modus ponens to a fixpoint, else 'cannot be determined') on the earlier
conditional_chain and on conditional_chain_r5; the queue index arithmetic on the earlier containers_queue_line_r2 and on _r5. 300 items per
level, seed base 8700 (throwaway). Accuracy per level.
usage: PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 uv run --locked python <this>"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import gen4
from studies.m0 import lineages_r1_clusters_v2 as v2
OLD = {x.id: x for x in v2.registered_v2()}
NEW = gen4.lineages()

def fc(b):
    st = b.structured
    known = {v: bb for v, bb in st["facts"]}
    rules = [([(v, bb) for v, bb in a], (c[0], c[1])) for a, c in st["rules"]]
    ch = True
    while ch:
        ch = False
        for a, (cv, cb) in rules:
            if all(known.get(v) == bb for v, bb in a) and cv not in known:
                known[cv] = cb; ch = True
    q = st["query"]
    return ("yes" if known[q] else "no") if q in known else "cannot be determined"

def arith(b):
    st = b.structured; j = st["ask"][1]; ops = st["ops"]
    c = {k: sum(1 for o in ops if o[0] == k) for k in ("serve", "cut", "leave", "front_to_back")}
    i = j - 1 + c["serve"] + c["front_to_back"] + c["leave"] - c["cut"]
    return st["line"][i] if 0 <= i < len(st["line"]) else None

for name, f, lins in (("forward chaining", fc, [OLD["R1.conditional_chain"], NEW["R1.conditional_chain_r5"]]), ("queue index arithmetic", arith, [OLD["R1.containers_queue_line_r2"], NEW["R1.containers_queue_line_r5"]])):
    for lin in lins:
        accs = []
        for lv in range(7):
            its = gen4.items(lin, lv, 300, 8700)
            accs.append(sum(f(b) == b.answer for b in its) / len(its))
        print(f"{name:24s} {lin.id:34s} " + " ".join(f"{a:.3f}" for a in accs))
