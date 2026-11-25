# ruff: noqa
"""Audit 4 (R1): item generation with throwaway seeds (NOT registered study seeds).

Items for lineage L, level v come from random.Random(SEED_BASE + v); L.build(v, rng) is called and core.Retry
is skipped (the same rng continues). Only the generators and the set definition (registered_v3) are imported;
nothing from any *_analysis module, the implementer's battery, gate, capacity or tables.
"""
import random, sys

sys.path.insert(0, ".")
from studies.m0.core import Retry  # the exception type only
from studies.m0.lineages_r1_fix3_clusters import registered_v3, NOT_REGISTERED_V3  # the set under audit
from studies.m0.lineages_r1_fix3_common import load_fix3


def lineages():
    return {l.id: l for l in registered_v3()}


def excluded():
    return {l.id: l for l in load_fix3() if l.id in NOT_REGISTERED_V3}


def items(lin, level, n, seed_base=3100, count_retries=False):
    r = random.Random(seed_base + level)
    out, retries = [], 0
    while len(out) < n:
        try:
            out.append(lin.build(level, r))
        except Retry:
            retries += 1
            if retries > 500 * n:
                raise RuntimeError(f"{lin.id} level {level}: too many retries")
    return (out, retries) if count_retries else out
