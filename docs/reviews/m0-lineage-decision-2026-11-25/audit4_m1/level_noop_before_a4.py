# ruff: noqa
"""Audit 4 of M1: the level no-op test of level_profile_a4.py applied to the PRE-FIX shape each r3 lineage revises (for comparison). Seed 13."""
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from level_profile_a4 import after, before, old_for, noop
from multiprocessing import get_context


def one(o):
    return o, noop(before()[o])


if __name__ == "__main__":
    A, B = after(), before()
    olds = sorted({old_for(i, B) for i in A if old_for(i, B)} - {"M1.digit_puzzle_r2"})
    with get_context("spawn").Pool(12) as p:
        res = dict(p.map(one, olds, chunksize=1))
    for o in olds:
        r = res[o]
        print(f"{o:34s} identical-levels {[f'{a}={a+1}' for a in range(6) if r[f'{a}-{a+1}'] == 1.0]}")
