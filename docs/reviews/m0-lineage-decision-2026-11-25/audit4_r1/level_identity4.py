# ruff: noqa
"""Audit 4 (R1): are two levels of a shape the SAME distribution? With one seed, build 200 items at level a and at level b from
random.Random(seed) (Retry skipped, same rng); if every question and answer coincide, the level does not enter the builder between a
and b (identical generator). Prints, per shape, the classes of levels that produce identical streams. Seeds 4242 and 777 (throwaway).
usage: PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 uv run --locked python <this>"""
import os, random, sys
sys.path.insert(0, os.path.dirname(__file__))
import gen4
from studies.m0.core import Retry

def stream(lin, lv, seed, n=200):
    r = random.Random(seed); out = []
    while len(out) < n:
        try:
            b = lin.build(lv, r); out.append((b.question, b.answer))
        except Retry:
            pass
    return out

L = gen4.lineages()
for lid in sorted(L):
    classes = []
    for lv in range(7):
        s = (stream(L[lid], lv, 4242), stream(L[lid], lv, 777, 50))
        for c in classes:
            if c[1] == s:
                c[0].append(lv); break
        else:
            classes.append([[lv], s])
    groups = [c[0] for c in classes]
    flag = "  <- levels share a generator" if len(groups) < 7 else ""
    print(f"{lid:38s} distinct level distributions {len(groups)}: {groups}{flag}")
